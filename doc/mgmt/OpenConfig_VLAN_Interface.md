# Add support for VLAN interface using OpenConfig YANG.

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
      * [3.3.1 REST API Support](#331-rest-api-support)
      * [3.3.2 gNMI Support](#332-gnmi-support)
      * [3.3.3 gNMI Subscription Support](#333-gnmi-subscription-support)
  * [4 Flow Diagrams](#4-flow-diagrams)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)
[Table 2: OpenConfig YANG SONiC YANG Mapping](#4-flow-diagrams)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 05/13/2025  | Allen Ting | Initial version                              |

# About this Manual
This document provides general information about the OpenConfig configuration of VLAN interface & VLAN member in SONiC.

# Scope
- This document describes the high level design of configuration of VLAN interfaces and members using openconfig models via REST & gNMI. 
- This does not cover the SONiC KLISH CLI.
- This covers only the VLAN interface/member configuration.
- This does not support subinterfaces configuration.
- Supported attributes in OpenConfig YANG tree (new attributes bolded):

<pre>
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
      |  +--ro counters
      +--rw subinterfaces
      +--rw oc-eth:ethernet
      <b>|  +--rw oc-vlan:switched-vlan
      |  |  +--rw oc-vlan:config
      |  |  |  +--rw oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
      |  |  |  +--rw oc-vlan:access-vlan?      oc-vlan-types:vlan-id
      |  |  |  +--rw oc-vlan:trunk-vlans*      union
      |  |  +--ro oc-vlan:state
      |  |     +--ro oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
      |  |     +--ro oc-vlan:access-vlan?      oc-vlan-types:vlan-id
      |  |     +--ro oc-vlan:trunk-vlans*      union</b>
      +--rw oc-lag:aggregation
      <b>|  +--rw oc-vlan:switched-vlan
      |  |  +--rw oc-vlan:config
      |  |  |  +--rw oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
      |  |  |  +--rw oc-vlan:access-vlan?      oc-vlan-types:vlan-id
      |  |  |  +--rw oc-vlan:trunk-vlans*      union
      |  |  +--ro oc-vlan:state
      |  |     +--ro oc-vlan:interface-mode?   oc-vlan-types:vlan-mode-type
      |  |     +--ro oc-vlan:access-vlan?      oc-vlan-types:vlan-id
      |  |     +--ro oc-vlan:trunk-vlans*      union</b>
      <b>+--rw oc-vlan:routed-vlan
      |  +--rw oc-vlan:config
      |  |  +--rw oc-vlan:vlan?   union
      |  +--ro oc-vlan:state
      |  |  +--ro oc-vlan:vlan?   union
      |  +--rw oc-ip:ipv4
      |  |  +--rw oc-ip:addresses
      |  |  |  +--rw oc-ip:address* [ip]
      |  |  |     +--rw oc-ip:ip        -> ../config/ip
      |  |  |     +--rw oc-ip:config
      |  |  |     |  +--rw oc-ip:ip?              oc-inet:ipv4-address
      |  |  |     |  +--rw oc-ip:prefix-length?   uint8
      |  |  |     +--ro oc-ip:state
      |  |  |     |  +--ro oc-ip:ip?              oc-inet:ipv4-address
      |  |  |     |  +--ro oc-ip:prefix-length?   uint8
      |  +--rw oc-ip:ipv6
      |     +--rw oc-ip:addresses
      |     |  +--rw oc-ip:address* [ip]
      |     |     +--rw oc-ip:ip        -> ../config/ip
      |     |     +--rw oc-ip:config
      |     |     |  +--rw oc-ip:ip?              oc-inet:ipv6-address
      |     |     |  +--rw oc-ip:prefix-length    uint8
      |     |     +--ro oc-ip:state
      |     |     |  +--ro oc-ip:ip?                  oc-inet:ipv6-address
      |     |     |  +--ro oc-ip:prefix-length        uint8
      |     +--rw oc-ip:config
      |     |  +--rw oc-ip:enabled?           boolean
      |     +--ro oc-ip:state
      |     |  +--ro oc-ip:enabled?           boolean</b>
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models.
2. Configure/Set, GET, and Delete VLAN interface attributes.
3. Support addition/deletion of Ethernet and PortChannel interfaces as VLAN members.
4. Support IPv4 and IPv6 address configuration on VLAN interfaces via REST and gNMI.

### 1.1.2 Configuration and Management Requirements
The VLAN interface and member configurations can be done via REST and gNMI. The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists.

### 1.1.3 Scalability Requirements
To be added.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports VLAN interface configurations such as GET, PATCH and DELETE via REST and gNMI using SONiC based YANG models. This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform PATCH, DELETE, POST, PUT, and GET operations on the supported YANG paths.
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
Sample GET output on VLAN interface without IP configuration: 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"enabled":true,"name":"Vlan10"},"name":"Vlan10","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan10"}}]}
```
With IPv4 configuration: 
```
{"openconfig-interfaces:interface":[{"config":{"enabled":true,"name":"Vlan10"},"name":"Vlan10","openconfig-vlan:routed-vlan":{"config":{"vlan":"Vlan10"},"openconfig-if-ip:ipv4":{"addresses":{"address":[{"config":{"ip":"133.3.3.4","prefix-length":24},"ip":"133.3.3.4","state":{"ip":"133.3.3.4","prefix-length":24}}]}},"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}},"state":{"vlan":"Vlan10"}},"state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan10"}}]}
```
With IPv6 configuration: 
```
{"openconfig-interfaces:interface":[{"config":{"enabled":true,"name":"Vlan10"},"name":"Vlan10","openconfig-vlan:routed-vlan":{"config":{"vlan":"Vlan10"},"openconfig-if-ip:ipv6":{"addresses":{"address":[{"config":{"ip":"12::13","prefix-length":64},"ip":"12::13","state":{"ip":"12::13","prefix-length":64}},{"ip":"fe80::1a5a:58ff:fef9:4325","state":{"ip":"fe80::1a5a:58ff:fef9:4325","prefix-length":64}}]},"config":{"enabled":true},"state":{"enabled":true}},"state":{"vlan":"Vlan10"}},"state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan10",}}]}
```
Sample GET output on Ethernet interface as a member of VLAN (trunk): 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan" -H "accept: application/yang-data+json"
{"openconfig-vlan:switched-vlan":{"config":{"interface-mode":"TRUNK","trunk-vlans":[10]},"state":{"interface-mode":"TRUNK","trunk-vlans":[10]}}}
```
Sample GET output on Ethernet interface as a member of VLAN (trunk, multiple VLANs):
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan" -H "accept: application/yang-data+json"
{"openconfig-vlan:switched-vlan":{"config":{"interface-mode":"TRUNK","trunk-vlans":[10,20,30]},"state":{"interface-mode":"TRUNK","trunk-vlans":[10,20,30]}}}
```
Sample GET output on PortChannel interface as a member of VLAN (access): 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel100/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan" -H "accept: application/yang-data+json"
{"openconfig-vlan:switched-vlan":{"config":{"access-vlan":10,"interface-mode":"ACCESS"},"state":{"access-vlan":10,"interface-mode":"ACCESS"}}}
```
Sample GET output on Ethernet interface as a member of VLAN (access + trunk): 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan" -H "accept: application/yang-data+json"
{"openconfig-vlan:switched-vlan":{"config":{"access-vlan":10,"interface-mode":"TRUNK","trunk-vlans":[20,30]},"state":{"access-vlan":10,"interface-mode":"TRUNK","trunk-vlans":[20,30]}}}
```
Sample GET output for multiple VLAN interfaces (top level): 
```
curl -X GET -k "https://100.94.113.29/restconf/data/openconfig-interfaces:interfaces" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interfaces":{"interface":[{"config":{"enabled":true,"mtu":9200,"name":"Vlan10"},"name":"Vlan10","openconfig-vlan:routed-vlan":{"config":{"vlan":"Vlan10"},"openconfig-if-ip:ipv4":{"addresses":{"address":[{"config":{"ip":"133.3.3.4","prefix-length":24},"ip":"133.3.3.4","state":{"ip":"133.3.3.4","prefix-length":24}}]}},"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}},"state":{"vlan":"Vlan10"}},"state":{"admin-status":"UP","enabled":true,"mtu":9200,"name":"Vlan10"}},{"config":{"enabled":true,"name":"Vlan20"},"name":"Vlan20","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan20"}},{"config":{"enabled":true,"name":"Vlan30"},"name":"Vlan30","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","enabled":true,"mtu":9100,"name":"Vlan30"}},{"config":{"description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan40"},"name":"Vlan40","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan40"}}]}}
```

#### 3.3.1.2 PUT
Supported at leaf level as well. Sample PUT to create a new VLAN Interface:
```
curl -X PUT -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-interfaces:interface\":[{\"name\":\"Vlan10\",\"config\":{\"name\":\"Vlan10\",\"mtu\":9000,\"description\":\"test_vlan\",\"enabled\":true}}]}"
```
Sample Verify VLAN PUT with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" -H "accept: application/yang-data+json"
{"openconfig-interfaces:interface":[{"config":{"description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan10"},"name":"Vlan10","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan10"}}]}
```

#### 3.3.1.2 POST
Supported at leaf level as well. Sample POST to update an existing VLAN Interface:
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan40" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-interfaces:config\":{\"name\":\"Vlan40\",\"mtu\":9000,\"description\":\"test_vlan\",\"enabled\":true}}"
```
Sample Verify VLAN POST with GET:
```
{"openconfig-interfaces:interface":[{"config":{"description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan40"},"name":"Vlan40","openconfig-vlan:routed-vlan":{"openconfig-if-ip:ipv6":{"config":{"enabled":false},"state":{"enabled":false}}},"state":{"admin-status":"UP","description":"test_vlan","enabled":true,"mtu":9000,"name":"Vlan40"}}]}
```

#### 3.3.1.3 PATCH
Supported at leaf level as well. Example for PATCH at leaf level MTU:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10/config/mtu" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-interfaces:mtu\":9000}"
```
Sample Verify VLAN PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10/config" -H "accept: application/yan
g-data+json"
{"openconfig-interfaces:config":{"enabled":true,"mtu":9000,"name":"Vlan10"}}
```
Sample PATCH to add Ethernet interface as a VLAN member (config level):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-vlan:config\":{\"interface-mode\":\"ACCESS\",\"access-vlan\":10}}"
```
Sample Verify VLAN member PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config" -H "accept: application/yang-data+json"
{"openconfig-vlan:config":{"access-vlan":10,"interface-mode":"ACCESS"}}
```
Sample PATCH to add PortChannel interface as a VLAN member (leaf level):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel100/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config/trunk-vlans" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-vlan:trunk-vlans\":[10,20,30,40]}"
```

Sample Verify VLAN PortChannel member PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel100/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config/trunk-vlans" -H "accept: application/yang-data+json"
{"openconfig-vlan:trunk-vlans":[10,20,30,40]}
```

#### 3.3.1.4 DELETE
Supported at leaf level as well.
Example for DELETE of VLAN member (Ethernet interface):
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Ethernet0/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/access-vlan" -H "accept: */*"
```
Example for DELETE of VLAN member (PortChannel Interface):
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel100/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config/trunk-vlans" -H "accept: */*"
```
Example for DELETE of VLAN interface:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" -H "accept: */*"
```

### 3.3.2 gNMI Support
#### 3.3.2.1 GET
VLAN interface GET:
```
gnmi_get -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath /openconfig-interfaces:interfaces/interface[name=Vlan10]/config
```
Response:
```
== getResponse:
notification: <
  timestamp: 1748360651441367172
  prefix: <
  >
  update: <
    path: <
      elem: <
        name: "openconfig-interfaces:interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Vlan10"
        >
      >
      elem: <
        name: "config"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-interfaces:config\":{\"enabled\":true,\"mtu\":9100,\"name\":\"Vlan10\"}}"
    >
  >
>
```

VLAN member GET:
```
gnmi_get -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/access-vlan
```
Response:
```
== getResponse:
notification: <
  timestamp: 1748360933199402296
  prefix: <
  >
  update: <
    path: <
      elem: <
        name: "openconfig-interfaces:interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Ethernet0"
        >
      >
      elem: <
        name: "openconfig-if-ethernet:ethernet"
      >
      elem: <
        name: "openconfig-vlan:switched-vlan"
      >
      elem: <
        name: "config"
      >
      elem: <
        name: "access-vlan"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-vlan:access-vlan\":20}"
    >
  >
>
```

#### 3.3.2.2 SET
VLAN interface SET:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -update /openconfig-interfaces:interfaces/interface[name=Vlan10]/config/mtu:@/host_home/admin/vlanParams.json

vlanParams.json:
{
  "openconfig-interfaces:mtu": 9000
}
```
GET response:
```
== getResponse:
notification: <
  timestamp: 1748361538102868503
  prefix: <
  >
  update: <
    path: <
      elem: <
        name: "openconfig-interfaces:interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Vlan10"
        >
      >
      elem: <
        name: "config"
      >
      elem: <
        name: "mtu"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-interfaces:mtu\":9000}"
    >
  >
>
```

VLAN member SET:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -update /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config:@/host_home/admin/vlanParams.json

vlanParams.json:
{
  "openconfig-vlan:config": {
    "interface-mode": "TRUNK",
    "access-vlan": 10,
    "trunk-vlans": [
      20,30
    ]
  }
}
```
GET response:
```
== getResponse:
notification: <
  timestamp: 1748361802519711977
  prefix: <
  >
  update: <
    path: <
      elem: <
        name: "openconfig-interfaces:interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Ethernet0"
        >
      >
      elem: <
        name: "openconfig-if-ethernet:ethernet"
      >
      elem: <
        name: "openconfig-vlan:switched-vlan"
      >
      elem: <
        name: "config"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-vlan:config\":{\"access-vlan\":10,\"interface-mode\":\"TRUNK\",\"trunk-vlans\":[20,30]}}"
    >
  >
>
```

#### 3.3.2.3 DELETE
VLAN member DELETE:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -delete /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config
```
GET Response:
```
== getResponse:
notification: <
  timestamp: 1748362174006779453
  prefix: <
  >
  update: <
    path: <
      elem: <
        name: "openconfig-interfaces:interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Ethernet0"
        >
      >
      elem: <
        name: "openconfig-if-ethernet:ethernet"
      >
      elem: <
        name: "openconfig-vlan:switched-vlan"
      >
      elem: <
        name: "config"
      >
    >
    val: <
      json_ietf_val: "{}"
    >
  >
>
```
VLAN interface DELETE:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -delete /openconfig-interfaces:interfaces/interface[name=Vlan10]
```
GET Response:
```
== getRequest:
prefix: <
>
path: <
  elem: <
    name: "openconfig-interfaces:interfaces"
  >
  elem: <
    name: "interface"
    key: <
      key: "name"
      value: "Vlan10"
    >
  >
>
encoding: JSON_IETF

Get failed: rpc error: code = NotFound desc = Resource not found
```

### 3.3.3 gNMI Subscription Support
#### 3.3.3.1 On Change
VLAN interface config (config level):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-interfaces:interfaces/interface[name=Vlan10]/config --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "enabled": true,
            "name": "Vlan10",
            "type": "l2vlan"
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "mtu": 9100
          }
        }
      }
    }
  }
}
```

VLAN interface config (wildcard):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-interfaces:interfaces/interface[name=*]/config --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "mtu": 9100
          }
        }
      }
    }
  }
}
```

VLAN interface IPv6 address config (wildcard):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv6": {
              "addresses": {
                "address": {
                  "fe80::1a5a:58ff:fef9:4325": {
                    "config": {
                      "ip": "fe80::1a5a:58ff:fef9:4325"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv6": {
              "addresses": {
                "address": {
                  "fe80::1a5a:58ff:fef9:4325": {
                    "config": {
                      "prefix-length": 64
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv6": {
              "addresses": {
                "address": {
                  "fe80::1a5a:58ff:fef9:4325": {
                    "state": {
                      "ip": "fe80::1a5a:58ff:fef9:4325"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv6": {
              "addresses": {
                "address": {
                  "fe80::1a5a:58ff:fef9:4325": {
                    "state": {
                      "prefix-length": 64
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```


VLAN member config (leaf):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config/trunk-vlans --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "trunk-vlans": [
                  20,
                  30
                ]
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "trunk-vlans": [
                  20
                ]
              }
            }
          }
        }
      }
    }
  }
}
```

VLAN member config (switched-vlan level):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "access-vlan": 10,
                "interface-mode": "ACCESS"
              },
              "state": {
                "access-vlan": 10
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "access-vlan": 20
              }
            }
          }
        }
      }
    }
  }
}
```

#### 3.3.3.2 SAMPLE

VLAN member config (config level):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-interfaces:interfaces/interface[name=Ethernet0]/openconfig-if-ethernet:ethernet/openconfig-vlan:switched-vlan/config --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "interface-mode": "TRUNK",
                "trunk-vlans": [
                  20,
                  30
                ]
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "trunk-vlans": [
                  20,
                  30
                ]
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "interface-mode": "TRUNK"
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Ethernet0": {
          "openconfig-if-ethernet:ethernet": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "access-vlan": 10
              }
            }
          }
        }
      }
    }
  }
}
```

VLAN PortChannel member config (config level):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-interfaces:interfaces/interface[name=PortChannel12]/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config --with_user_pass
```
Example Output:
```
{}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "PortChannel12": {
          "openconfig-if-aggregate:aggregation": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "access-vlan": 10
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "PortChannel12": {
          "openconfig-if-aggregate:aggregation": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "interface-mode": "ACCESS"
              }
            }
          }
        }
      }
    }
  }
}
```

VLAN interface config (leaf):
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-interfaces:interfaces/interface[name=Vlan10]/config/mtu --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "mtu": 9100
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "mtu": 9200
          }
        }
      }
    }
  }
}
```

VLAN interface IPv4 config:
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-interfaces:interfaces/interface[name=Vlan10]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4 --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv4": {
              "addresses": {
                "address": {
                  "133.3.3.4": {
                    "state": {
                      "ip": "133.3.3.4"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "openconfig-vlan:routed-vlan": {
            "openconfig-if-ip:ipv4": {
              "addresses": {
                "address": {
                  "133.3.3.4": {
                    "state": {
                      "prefix-length": 24
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

#### 3.3.3.4 Target Defined
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type s -query /openconfig-interfaces:interfaces/interface[name=PortChannel100]/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan/config --with_user_pass
```
Example Output:
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "enabled": true,
            "mtu": 9000,
            "name": "Vlan10",
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "Vlan10": {
          "config": {
            "mtu": 9200
          }
        }
      }
    }
  }
}
```
```
{
  "OC_YANG": {
    "openconfig-interfaces:interfaces": {
      "interface": {
        "PortChannel100": {
          "openconfig-if-aggregate:aggregation": {
            "openconfig-vlan:switched-vlan": {
              "config": {
                "trunk-vlans": [
                  10,
                  20,
                  30
                ]
              }
            }
          }
        }
      }
    }
  }
}
```

# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and Community SONiC YANG:

|   OpenConfig YANG (openconfig-interfaces.yang)       |    SONiC YANG (sonic-vlan.yang)    |
|----------------------------------------------|------------------------------------|
|                                              |    *container VLAN*                |
|   name                                       |    name                            |
|   mtu                                        |    mtu                             | 
|   enabled                                    |    admin_status                    |
|   vlan-id (openconfig-vlan.yang)             |    vlanid                          |


|   OpenConfig YANG (openconfig-vlan.yang)             |    SONiC YANG (sonic-vlan.yang)    |
|----------------------------------------------|------------------------------------|
|                                              |    *container VLAN_MEMBER*         |
|   name                                       |    name                            |
|                                              |    tagging_mode (derived)          |
|   name (openconfig-interfaces.yang)          |    port                            |


|   OpenConfig YANG (openconfig-if-ip.yang)            |  SONiC YANG (sonic-vlan.yang)      |
|----------------------------------------------|------------------------------------|
|                                              |  *container VLAN_INTERFACE*        |
|   name                                       |    name                            |
|   enabled                                    |    ipv6_use_link_local_only        | 
|   ip + prefix-length                         |    ip-prefix                       |


# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Create, verify, and delete VLAN interface using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
2. Verify GET, PATCH, PUT, POST and DELETE for L3 configurations (ip address, prefix-length, and ipv6 enabled) on VLAN interface works as expected via REST/gNMI.
3. Verify that enable/disable of attribute **ipv6 enabled** works as expected via REST and gNMI.
4. Verify GET, PATCH, PUT, and DELETE for VLAN interface attribute **mtu** works as expected via REST/gNMI.
5. Verify GET, PATCH, PUT, and DELETE for VLAN interface attribute **admin_status** works as expected via REST/gNMI.
6. Verify GET, PATCH, PUT, POST, and DELETE for VLAN members (physical Ethernet and PortChannel, trunk and access).
7. Verify gNMI subscription (on change, sample, target defined) for VLAN interface and member configurations works as expected.

## 6.2 Negative Test Cases
1. Verify GET after DELETE returns a "Resource Not Found" error.

GET deleted VLAN interface:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-interfaces:interfaces/interface=Vlan10" -H "accept: application/yang-data+json"

{"ietf-restconf:errors":{"error":[{"error-type":"application","error-tag":"invalid-value","error-message":"Resource not found"}]}}
```
