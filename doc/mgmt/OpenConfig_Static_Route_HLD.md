# OpenConfig Support for Static Route.

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
| 0.1 | 12/02/2025  | GitHub Copilot | Initial version                              |

# About this Manual
This document provides general information about the OpenConfig configuration of Static Routes in SONiC.

# Scope
- This document describes the high level design of configuration of Static Routes using openconfig models via REST & gNMI. 
- This does not cover the SONiC KLISH CLI.
- This covers only the Static Route configuration.
- Supported attributes in OpenConfig YANG tree (new attributes bolded):

<pre>
module: openconfig-network-instance
+--rw network-instances
   +--rw network-instance* [name]
      +--rw name                     -> ../config/name
      +--rw config
      |  +--rw name?                 string
      |  +--rw type?                 identityref
      |  +--rw enabled?              boolean
      +--ro state
      |  +--ro name?                 string
      |  +--ro type?                 identityref
      |  +--ro enabled?              boolean
      <b>+--rw protocols
      |  +--rw protocol* [identifier name]
      |     +--rw identifier         -> ../config/identifier
      |     +--rw name               -> ../config/name
      |     +--rw config
      |     |  +--rw identifier?     identityref
      |     |  +--rw name?           string
      |     |  +--rw enabled?        boolean
      |     +--ro state
      |     |  +--ro identifier?     identityref
      |     |  +--ro name?           string
      |     |  +--ro enabled?        boolean
      |     +--rw static-routes
      |        +--rw static* [prefix]
      |           +--rw prefix           -> ../config/prefix
      |           +--rw config
      |           |  +--rw prefix?       oc-inet:ip-prefix
      |           |  +--rw set-tag?      oc-pol-types:tag-type
      |           +--ro state
      |           |  +--ro prefix?       oc-inet:ip-prefix
      |           |  +--ro set-tag?      oc-pol-types:tag-type
      |           +--rw next-hops
      |              +--rw next-hop* [index]
      |                 +--rw index         -> ../config/index
      |                 +--rw config
      |                 |  +--rw index?           string
      |                 |  +--rw next-hop?        oc-inet:ip-address-no-zone
      |                 |  +--rw interface-ref?   -> /oc-if:interfaces/interface/name
      |                 |  +--rw recurse?         boolean
      |                 |  +--rw metric?          uint32
      |                 +--ro state
      |                 |  +--ro index?           string
      |                 |  +--ro next-hop?        oc-inet:ip-address-no-zone
      |                 |  +--ro interface-ref?   -> /oc-if:interfaces/interface/name
      |                 |  +--ro recurse?         boolean
      |                 |  +--ro metric?          uint32
      |                 +--rw enable-bfd
      |                    +--rw config
      |                    |  +--rw enabled?       boolean
      |                    +--ro state
      |                       +--ro enabled?       boolean</b>
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |
| BFD                     | Bidirectional Forwarding Detection   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models for Static Routes.
2. Configure/Set, GET, and Delete Static Route attributes including prefix, next-hop, interface, and BFD configuration.
3. Support IPv4 and IPv6 static route configuration with multiple next-hop types (IP address, interface, Null0/DROP).
4. Support BFD (Bidirectional Forwarding Detection) configuration for static routes.

### 1.1.2 Configuration and Management Requirements
The Static Route configurations can be done via REST and gNMI. The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists.

### 1.1.3 Scalability Requirements
To be added.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports Static Route configurations such as GET, PATCH and DELETE via REST and gNMI using SONiC based YANG models. This feature adds support for OpenConfig based YANG models using transformer based implementation instead of translib infra.
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
Sample GET output on Static Route with IP next-hop: 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"1","next-hop":"10.1.1.1"},"index":"1","state":{"index":"1","next-hop":"10.1.1.1"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```
With BFD configuration: 
```
{"openconfig-network-instance:static":[{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"1","state":{"index":"1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}}]}
```
With interface next-hop: 
```
{"openconfig-network-instance:static":[{"config":{"prefix":"2004::/64"},"next-hops":{"next-hop":[{"config":{"index":"1","interface-ref":"Loopback0"},"index":"1","state":{"index":"1","interface-ref":"Loopback0"}}]},"prefix":"2004::/64","state":{"prefix":"2004::/64"}}]}
```
Sample GET output on Static Route with Null0 interface (DROP): 
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"1","interface-ref":"Null0"},"index":"1","state":{"index":"1","interface-ref":"Null0"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```
Sample GET output for multiple Static Routes (top level): 
```
curl -X GET -k "https://100.94.113.29/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static-routes":{"static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"1","interface-ref":"Null0"},"index":"1","state":{"index":"1","interface-ref":"Null0"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}},{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"1","state":{"index":"1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}},{"config":{"prefix":"2004::/64"},"next-hops":{"next-hop":[{"config":{"index":"1","interface-ref":"Loopback0"},"index":"1","state":{"index":"1","interface-ref":"Loopback0"}}]},"prefix":"2004::/64","state":{"prefix":"2004::/64"}}]}}
```

#### 3.3.1.2 PUT
Supported at leaf level as well. Sample PUT to create a new Static Route:
```
curl -X PUT -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:static\":[{\"prefix\":\"172.16.0.0/24\",\"config\":{\"prefix\":\"172.16.0.0/24\"},\"next-hops\":{\"next-hop\":[{\"index\":\"1\",\"config\":{\"index\":\"1\",\"interface-ref\":\"Null0\"}}]}}]}"
```
Sample Verify Static Route PUT with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"1","interface-ref":"Null0"},"index":"1","state":{"index":"1","interface-ref":"Null0"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```

#### 3.3.1.3 POST
Supported at leaf level as well. Sample POST to update an existing Static Route:
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:next-hops\":{\"next-hop\":[{\"index\":\"1\",\"config\":{\"index\":\"1\",\"next-hop\":\"10.1.1.1\"},\"enable-bfd\":{\"config\":{\"enabled\":true}}}]}}"
```
Sample Verify Static Route POST with GET:
```
{"openconfig-network-instance:static":[{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"1","state":{"index":"1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}}]}
```

#### 3.3.1.4 PATCH
Supported at leaf level as well. Example for PATCH at leaf level next-hop:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24/next-hops/next-hop=1/config/next-hop" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:next-hop\":\"192.168.1.1\"}"
```
Sample Verify Static Route PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24/next-hops/next-hop=1/config" -H "accept: application/yang-data+json"
{"openconfig-network-instance:config":{"index":"1","next-hop":"192.168.1.1"}}
```
Sample PATCH to add IPv6 static route with interface next-hop:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=2004::/64/next-hops/next-hop=1/config" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:config\":{\"index\":\"1\",\"interface-ref\":\"Loopback0\"}}"
```
Sample Verify IPv6 Static Route PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=2004::/64/next-hops/next-hop=1/config" -H "accept: application/yang-data+json"
{"openconfig-network-instance:config":{"index":"1","interface-ref":"Loopback0"}}
```
Sample PATCH to enable BFD on static route (leaf level):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=1/enable-bfd/config/enabled" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:enabled\":true}"
```

Sample Verify BFD Static Route PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=1/enable-bfd/config/enabled" -H "accept: application/yang-data+json"
{"openconfig-network-instance:enabled":true}
```

#### 3.3.1.5 DELETE
Supported at leaf level as well.
Example for DELETE of Static Route next-hop:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24/next-hops/next-hop=1/config/next-hop" -H "accept: */*"
```
Example for DELETE of BFD configuration:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=1/enable-bfd" -H "accept: */*"
```
Example for DELETE of entire Static Route:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: */*"
```

### 3.3.2 gNMI Support
#### 3.3.2.1 GET
Static Route GET:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]"
```
Response:
```
== getResponse:
[
  {
    "source": "172.29.94.36:17439",
    "timestamp": 1764743588352078034,
    "time": "2025-12-03T12:03:08.352078034+05:30",
    "target": "OC-YANG",
    "updates": [
      {
        "Path": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]",
        "values": {
          "openconfig-network-instance:network-instances/network-instance/protocols/protocol/static-routes/static": {
            "openconfig-network-instance:static": [
              {
                "config": {
                  "prefix": "172.16.0.0/24"
                },
                "next-hops": {
                  "next-hop": [
                    {
                      "config": {
                        "index": "DROP",
                        "next-hop": "DROP"
                      },
                      "index": "DROP",
                      "state": {
                        "index": "DROP",
                        "next-hop": "DROP"
                      }
                    }
                  ]
                },
                "prefix": "172.16.0.0/24",
                "state": {
                  "prefix": "172.16.0.0/24"
                }
              }
            ]
          }
        }
      }
    ]
  }
]
```

Static Route next-hop GET:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=51.3.0.0/16]/next-hops/next-hop[index="10.1.1.1"]/config/next-hop"
```
Response:
```
== getResponse:
[
  {
    "source": "172.29.94.36:17439",
    "timestamp": 1764743769335174839,
    "time": "2025-12-03T12:06:09.335174839+05:30",
    "target": "OC-YANG",
    "updates": [
      {
        "Path": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=51.3.0.0/16]/next-hops/next-hop[index=10.1.1.1]/config/next-hop",
        "values": {
          "openconfig-network-instance:network-instances/network-instance/protocols/protocol/static-routes/static/next-hops/next-hop/config/next-hop": {
            "openconfig-network-instance:next-hop": "10.1.1.1"
          }
        }
      }
    ]
  }
]
```

#### 3.3.2.2 SET
Create static route to Null0:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --update-path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]" --update-file static_route_null0.json

static_route_null0.json:

{
  "openconfig-network-instance:static": [{
    "prefix": "172.16.0.0/24",
    "config": {"prefix": "172.16.0.0/24"},
    "next-hops": {"next-hop": [{
      "index": "DROP",
      "config": {"index": "DROP", "next-hop": "DROP"}
    }]}
  }]
}
```
GET response:
```
== getResponse:
[
  {
    "source": "172.29.94.36:17439",
    "timestamp": 1764743942309599073,
    "time": "2025-12-03T12:09:02.309599073+05:30",
    "target": "OC-YANG",
    "updates": [
      {
        "Path": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]",
        "values": {
          "openconfig-network-instance:network-instances/network-instance/protocols/protocol/static-routes/static": {
            "openconfig-network-instance:static": [
              {
                "config": {
                  "prefix": "172.16.0.0/24"
                },
                "next-hops": {
                  "next-hop": [
                    {
                      "config": {
                        "index": "DROP",
                        "next-hop": "DROP"
                      },
                      "index": "DROP",
                      "state": {
                        "index": "DROP",
                        "next-hop": "DROP"
                      }
                    }
                  ]
                },
                "prefix": "172.16.0.0/24",
                "state": {
                  "prefix": "172.16.0.0/24"
                }
              }
            ]
          }
        }
      }
    ]
  }
]
```


#### 3.3.2.3 DELETE
Static Route next-hop DELETE:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --delete "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]"
```
GET Response:

gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes" 
```
== getResponse:
[
  {
    "source": "172.29.94.36:17439",
    "timestamp": 1764744114833239125,
    "time": "2025-12-03T12:11:54.833239125+05:30",
    "target": "OC-YANG",
    "updates": [
      {
        "Path": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes",
        "values": {
          "openconfig-network-instance:network-instances/network-instance/protocols/protocol/static-routes": {
            "openconfig-network-instance:static-routes": {
              "static": [
                {
                  "config": {
                    "prefix": "51.3.0.0/16"
                  },
                  "next-hops": {
                    "next-hop": [
                      {
                        "config": {
                          "index": "10.1.1.1",
                          "next-hop": "10.1.1.1"
                        },
                        "enable-bfd": {
                          "config": {
                            "enabled": true
                          },
                          "state": {
                            "enabled": true
                          }
                        },
                        "index": "10.1.1.1",
                        "state": {
                          "index": "10.1.1.1",
                          "next-hop": "10.1.1.1"
                        }
                      }
                    ]
                  },
                  "prefix": "51.3.0.0/16",
                  "state": {
                    "prefix": "51.3.0.0/16"
                  }
                },
                {
                  "config": {
                    "prefix": "2004::/64"
                  },
                  "next-hops": {
                    "next-hop": [
                      {
                        "config": {
                          "index": "LOCAL_LINK+Loopback0",
                          "next-hop": "LOCAL_LINK"
                        },
                        "index": "LOCAL_LINK+Loopback0",
                        "interface-ref": {
                          "config": {
                            "interface": "Loopback0"
                          },
                          "state": {
                            "interface": "Loopback0"
                          }
                        },
                        "state": {
                          "index": "LOCAL_LINK+Loopback0",
                          "next-hop": "LOCAL_LINK"
                        }
                      }
                    ]
                  },
                  "prefix": "2004::/64",
                  "state": {
                    "prefix": "2004::/64"
                  }
                }
              ]
            }
          }
        }
      }
    ]
  }
]
```

GET Response:

gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]"
```
== getRequest:
target "172.29.94.36:17439" Get request failed: "172.29.94.36:17439" GetRequest failed: rpc error: code = NotFound desc = Resource not found
Error: one or more requests failed
```

### 3.3.3 gNMI Subscription Support
#### 3.3.3.1 On Change
Static Route config (config level):
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf subscribe --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]/config" --mode stream --stream-mode on-change
```
Example Output:
```
{
  "source": "172.29.94.36:17439",
  "subscription-name": "default-1764744509",
  "timestamp": 1764744509102793598,
  "time": "2025-12-03T12:18:29.102793598+05:30",
  "prefix": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]/config",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "prefix",
      "values": {
        "prefix": "172.16.0.0/24"
      }
    }
  ]
}
{
  "sync-response": true
}
```

# 4 Flow Diagrams
Mapping attributes between OpenConfig YANG and Community SONiC YANG:

|   OpenConfig YANG (openconfig-network-instance.yang)  |    SONiC YANG (sonic-static-route.yang)    |
|----------------------------------------------|------------------------------------|
|                                              |    *container STATIC_ROUTE*        |
|   prefix                                     |    prefix                          |
|   next-hop                                   |    nexthop                         | 
|   interface-ref                              |    ifname                          |
|   enabled (enable-bfd)                       |    bfd                             |

|   OpenConfig YANG (openconfig-network-instance.yang)  |    SONiC YANG (sonic-vrf.yang)      |
|----------------------------------------------|------------------------------------|
|   name (network-instance)                    |    vrf_name                        |

# 5 Error Handling
Invalid configurations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Create, verify, and delete Static Routes using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
2. Verify GET, PATCH, PUT, POST and DELETE for IPv4 static routes with IP next-hop works as expected via REST/gNMI.
3. Verify GET, PATCH, PUT, POST and DELETE for IPv6 static routes with interface next-hop works as expected via REST/gNMI.
4. Verify GET, PATCH, PUT, and DELETE for static routes with Null0 interface (DROP) works as expected via REST/gNMI.
5. Verify GET, PATCH, PUT, and DELETE for BFD configuration on static routes works as expected via REST/gNMI.
6. Verify multiple next-hops per static route configuration works as expected via REST/gNMI.
7. Verify gNMI subscription (on change, sample, target defined) for static route configurations works as expected.
8. Verify static route configuration with different interface types (Ethernet, PortChannel, Loopback, Null0).
9. Verify static route metric configuration works as expected via REST/gNMI.
10. Verify static route tag configuration works as expected via REST/gNMI.

## 6.2 Negative Test Cases
1. Verify GET after DELETE returns a "Resource Not Found" error.

GET deleted Static Route:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"ietf-restconf:errors":{"error":[{"error-type":"application","error-tag":"invalid-value","error-message":"Resource not found"}]}}
```

2. Verify invalid prefix format returns appropriate error.
3. Verify invalid next-hop IP address returns appropriate error.
4. Verify non-existent interface reference returns appropriate error.
5. Verify conflicting next-hop configurations (both IP and interface) return appropriate error.
