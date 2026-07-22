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
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
      * [3.3.3 gNMI Support](#333-gnmi-support)
  * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)

# List of Tables
  * [Table 1: Abbreviations](#table-1-abbreviations)
  * [Table 2: CONFIG_DB STATIC_ROUTE Mapping](#table-2-config_db-static_route-mapping)
  * [Table 3: OpenConfig to SONiC Mapping Table](#table-3-openconfig-to-sonic-mapping-table)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 12/02/2025  | Raja Kushwah, Anukul Verma | Initial version |

# About this Manual
This document provides general information about the OpenConfig configuration of Static Routes in SONiC.

# Scope
- This document describes the high level design of configuration of Static Routes using openconfig models via REST & gNMI.
- This does not cover the SONiC KLISH CLI.
- This covers only Static Route configuration under:
  `/network-instances/network-instance/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes`
- Static routes are mapped to the existing CONFIG_DB `STATIC_ROUTE` table; no new DB schema is introduced.
- Supported attributes in OpenConfig YANG tree:

<pre>
module: openconfig-network-instance
+--rw network-instances
   +--rw network-instance* [name]
      +--rw name                     -> ../config/name
      +--rw protocols
         +--rw protocol* [identifier STATIC][name DEFAULT]
            +--rw static-routes
               +--rw static* [prefix]
                  +--rw prefix           -> ../config/prefix
                  +--rw config
                  |  +--rw prefix?       oc-inet:ip-prefix
                  +--ro state
                  |  +--ro prefix?       oc-inet:ip-prefix
                  +--rw next-hops
                     +--rw next-hop* [index]
                        +--rw index         -> ../config/index
                        +--rw config
                        |  +--rw index?           string
                        |  +--rw next-hop?        union (IP | LOCAL_LINK | DROP)
                        +--ro state
                        |  +--ro index?           string
                        |  +--ro next-hop?        union (IP | LOCAL_LINK | DROP)
                        +--rw interface-ref
                        |  +--rw config
                        |  |  +--rw interface?     -> /oc-if:interfaces/interface/name
                        |  |  +--rw subinterface?  uint32
                        |  +--ro state
                        |     +--ro interface?     -> /oc-if:interfaces/interface/name
                        |     +--ro subinterface?  uint32
                        +--rw oc-loc-rt-nw-inst:nh-network-instance?   string
                        +--ro oc-loc-rt-nw-inst:nh-network-instance?   string
                        +--rw enable-bfd
                           +--rw config
                           |  +--rw enabled?       boolean
                           +--ro state
                              +--ro enabled?       boolean
</pre>

Notes:
- `network-instance/name` maps to the VRF component of the CONFIG_DB key (`default`, `Vrf-*`, etc.).
- The next-hop list key `index` is derived from nexthop type; see [Translation Notes in §4](#4-openconfig-to-sonic-mapping-table).

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| REST | REpresentative State Transfer |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |
| BFD                     | Bidirectional Forwarding Detection   |
| VRF                     | Virtual Routing and Forwarding   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models for Static Routes.
2. Configure/Set, GET, and Delete Static Route attributes including prefix, next-hop, interface, nexthop VRF (`nh-network-instance`), and BFD enable.
3. Support IPv4 and IPv6 static route configuration with multiple next-hop types (IP address, interface-only LOCAL_LINK, and DROP/blackhole).
4. Support BFD enable on IP next-hops only.
5. Support multiple next-hops per prefix.

### 1.1.2 Configuration and Management Requirements
The Static Route configurations can be done via REST and gNMI. The implementation will return an error if a configuration is not allowed. No new configuration commands or methods are added beyond what already exists.

### 1.1.3 Scalability Requirements
Static route scale follows the existing CONFIG_DB `STATIC_ROUTE` schema and platform limits for the number of prefixes and next-hops per prefix.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports Static Route configurations such as GET, PATCH and DELETE via REST and gNMI using SONiC based YANG models. This feature adds support for OpenConfig based YANG models using transformer based implementation in *sonic-mgmt-common*.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform PATCH, DELETE, POST, PUT, and GET operations on the supported YANG paths.
2. gNMI client with support for capabilities get and set based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition. OpenConfig static routes are mapped to the existing `STATIC_ROUTE` table.

#### Table 2: CONFIG_DB STATIC_ROUTE Mapping
| CONFIG_DB item | Value / format |
|----------------|----------------|
| Table | `STATIC_ROUTE` |
| Key | `{vrf}\|{prefix}` e.g. `default\|172.16.0.0/24` |
| `nexthop` | Comma-separated list aligned per next-hop (IP, `0.0.0.0`/`::` for LOCAL_LINK/DROP) |
| `ifname` | Comma-separated interface list aligned per next-hop (`Null0` for DROP) |
| `nexthop-vrf` | Comma-separated VRF list aligned per next-hop (from `nh-network-instance`) |
| `bfd` | Comma-separated `true`/`false` list aligned per next-hop |

Example (IPv4 route with two next-hops: IP with BFD, then DROP):

```
STATIC_ROUTE|default|172.16.1.0/24
  nexthop:     192.168.1.1,0.0.0.0
  ifname:      Ethernet0,Null0
  nexthop-vrf: default,
  bfd:         true,false
```

For DROP on an IPv6 prefix, the no-gateway address stored in `nexthop` is `::` with `ifname=Null0`. OpenConfig represents the blackhole next-hop as `next-hop=DROP`; the CONFIG_DB stores the no-gateway address and `Null0` interface, not the literal string `DROP`.

The VRF component of the key comes from `network-instance/name`.

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
The OpenConfig YANG modules (`openconfig-network-instance.yang`, `openconfig-local-routing-network-instance.yang`) expose static routes under `/network-instances/network-instance/protocols/protocol/static-routes`. The SONiC internal model `sonic-static-route.yang` is used in the transformer mapping to CONFIG_DB.

- openconfig-network-instance.yang
- openconfig-local-routing-network-instance.yang
- sonic-static-route.yang

### 3.3.2 REST API Support
#### 3.3.2.1 GET
Supported at leaf level as well.

Sample GET output on Static Route with IP next-hop:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"10.1.1.1","next-hop":"10.1.1.1"},"index":"10.1.1.1","state":{"index":"10.1.1.1","next-hop":"10.1.1.1"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```

With BFD configuration:
```
{"openconfig-network-instance:static":[{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"10.1.1.1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"10.1.1.1","state":{"index":"10.1.1.1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}}]}
```

With interface next-hop (LOCAL_LINK):
```
{"openconfig-network-instance:static":[{"config":{"prefix":"2004::/64"},"next-hops":{"next-hop":[{"config":{"index":"LOCAL_LINK+Loopback0","next-hop":"LOCAL_LINK"},"index":"LOCAL_LINK+Loopback0","interface-ref":{"config":{"interface":"Loopback0"},"state":{"interface":"Loopback0"}},"state":{"index":"LOCAL_LINK+Loopback0","next-hop":"LOCAL_LINK"}}]},"prefix":"2004::/64","state":{"prefix":"2004::/64"}}]}
```

Sample GET output on Static Route with DROP (blackhole):
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"DROP","next-hop":"DROP"},"index":"DROP","state":{"index":"DROP","next-hop":"DROP"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```

Sample GET output for multiple Static Routes (top level):
```
curl -X GET -k "https://100.94.113.29/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static-routes":{"static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"DROP","next-hop":"DROP"},"index":"DROP","state":{"index":"DROP","next-hop":"DROP"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}},{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"10.1.1.1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"10.1.1.1","state":{"index":"10.1.1.1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}},{"config":{"prefix":"2004::/64"},"next-hops":{"next-hop":[{"config":{"index":"LOCAL_LINK+Loopback0","next-hop":"LOCAL_LINK"},"index":"LOCAL_LINK+Loopback0","interface-ref":{"config":{"interface":"Loopback0"},"state":{"interface":"Loopback0"}},"state":{"index":"LOCAL_LINK+Loopback0","next-hop":"LOCAL_LINK"}}]},"prefix":"2004::/64","state":{"prefix":"2004::/64"}}]}}
```

#### 3.3.2.2 PUT
Supported at leaf level as well. PUT performs REPLACE on the static route next-hop list.

Sample PUT to create a new Static Route with DROP next-hop:
```
curl -X PUT -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:static\":[{\"prefix\":\"172.16.0.0/24\",\"config\":{\"prefix\":\"172.16.0.0/24\"},\"next-hops\":{\"next-hop\":[{\"index\":\"DROP\",\"config\":{\"index\":\"DROP\",\"next-hop\":\"DROP\"}}]}}]}"
```

Sample Verify Static Route PUT with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: application/yang-data+json"
{"openconfig-network-instance:static":[{"config":{"prefix":"172.16.0.0/24"},"next-hops":{"next-hop":[{"config":{"index":"DROP","next-hop":"DROP"},"index":"DROP","state":{"index":"DROP","next-hop":"DROP"}}]},"prefix":"172.16.0.0/24","state":{"prefix":"172.16.0.0/24"}}]}
```

#### 3.3.2.3 POST
Supported at leaf level as well. POST merges next-hops into an existing static route.

Sample POST to add a next-hop with BFD on an existing prefix:
```
curl -X POST -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=10.1.1.1" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:next-hop\":{\"index\":\"10.1.1.1\",\"config\":{\"index\":\"10.1.1.1\",\"next-hop\":\"10.1.1.1\"},\"enable-bfd\":{\"config\":{\"enabled\":true}}}}"
```

Sample Verify Static Route POST with GET:
```
{"openconfig-network-instance:static":[{"config":{"prefix":"51.3.0.0/16"},"next-hops":{"next-hop":[{"config":{"index":"10.1.1.1","next-hop":"10.1.1.1"},"enable-bfd":{"config":{"enabled":true},"state":{"enabled":true}},"index":"10.1.1.1","state":{"index":"10.1.1.1","next-hop":"10.1.1.1"}}]},"prefix":"51.3.0.0/16","state":{"prefix":"51.3.0.0/16"}}]}
```

#### 3.3.2.4 PATCH
Supported at leaf level as well. Example for PATCH at leaf level next-hop:
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24/next-hops/next-hop=192.168.1.1/config/next-hop" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:next-hop\":\"192.168.1.2\"}"
```

Sample Verify Static Route PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24/next-hops/next-hop=192.168.1.1/config" -H "accept: application/yang-data+json"
{"openconfig-network-instance:config":{"index":"192.168.1.1","next-hop":"192.168.1.2"}}
```

Sample PATCH to merge a LOCAL_LINK next-hop (config and interface-ref) into an existing IPv6 prefix. Target the next-hop list entry, not `.../config` (PATCH to `/config` accepts only the config container):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=2004::/64/next-hops/next-hop=LOCAL_LINK+Loopback0" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:next-hop\":{\"index\":\"LOCAL_LINK+Loopback0\",\"config\":{\"index\":\"LOCAL_LINK+Loopback0\",\"next-hop\":\"LOCAL_LINK\"},\"interface-ref\":{\"config\":{\"interface\":\"Loopback0\"}}}}"
```

Sample PATCH to enable BFD on static route (leaf level):
```
curl -X PATCH -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=10.1.1.1/enable-bfd/config/enabled" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:enabled\":true}"
```

Sample Verify BFD Static Route PATCH with GET:
```
curl -X GET -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=10.1.1.1/enable-bfd/config/enabled" -H "accept: application/yang-data+json"
{"openconfig-network-instance:enabled":true}
```

#### 3.3.2.5 DELETE
Supported at leaf level as well.

Example for DELETE of one next-hop (allowed only when multiple next-hops exist):
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.1.0/24/next-hops/next-hop=192.168.1.1" -H "accept: */*"
```

Example for DELETE of BFD configuration:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=51.3.0.0/16/next-hops/next-hop=10.1.1.1/enable-bfd" -H "accept: */*"
```

Example for DELETE of entire Static Route:
```
curl -X DELETE -k "https://100.94.113.12/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=STATIC,DEFAULT/static-routes/static=172.16.0.0/24" -H "accept: */*"
```

DELETE restrictions are described in [Translation Notes in §4](#4-openconfig-to-sonic-mapping-table).

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
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
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=51.3.0.0/16]/next-hops/next-hop[index=10.1.1.1]/config/next-hop"
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

#### 3.3.3.2 SET
Create static route with DROP next-hop:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --update-path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]" --update-value '{
  "openconfig-network-instance:static": [{
    "prefix": "172.16.0.0/24",
    "config": {"prefix": "172.16.0.0/24"},
    "next-hops": {"next-hop": [{
      "index": "DROP",
      "config": {"index": "DROP", "next-hop": "DROP"}
    }]}
  }]
}'
```

#### 3.3.3.3 DELETE
Delete entire static route prefix:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf set --delete "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]"
```

#### 3.3.3.4 SUBSCRIBE
Supported.

Sample subscription on static route prefix config:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf subscribe --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]/config" --mode stream
```

Sample subscription on next-hops:
```
gnmic -a 172.29.94.36:17439 -u cisco -p cisco123 --insecure --target OC-YANG -e json_ietf subscribe --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes/static[prefix=172.16.0.0/24]/next-hops" --mode stream
```

# 4 OpenConfig to SONiC Mapping Table
Mapping attributes between OpenConfig YANG and CONFIG_DB `STATIC_ROUTE`:

#### Table 3: OpenConfig to SONiC Mapping Table

**Database Table:** STATIC_ROUTE  
**Key Pattern:** `{vrf}|{prefix}` (e.g. `default|172.16.0.0/24`)

| OpenConfig YANG Path | SONiC DB Table | SONiC DB Field | Notes |
|---------------------|----------------|----------------|--------|
| `/network-instances/network-instance/name` | STATIC_ROUTE | Key `{vrf}` | VRF name |
| `../protocol/static-routes/static/config/prefix` | STATIC_ROUTE | Key `{prefix}` | Normalized CIDR; `protocol[identifier=STATIC][name=DEFAULT]` only |
| `../static-routes/static/next-hops/next-hop/config/next-hop` | STATIC_ROUTE | nexthop | IP, LOCAL_LINK, or DROP encoding |
| `next-hop/interface-ref/config/interface` | STATIC_ROUTE | ifname | Required for LOCAL_LINK; optional with IP |
| `next-hop/interface-ref/config/subinterface` | STATIC_ROUTE | ifname | Encoded as `{interface}.{subinterface}` in DB |
| `next-hop/oc-loc-rt-nw-inst:nh-network-instance` | STATIC_ROUTE | nexthop-vrf | `default`, `mgmt`, `Vrf-*` |
| `next-hop/enable-bfd/config/enabled` | STATIC_ROUTE | bfd | IP next-hops only |

Translation Notes:
1. Only static routes under `/network-instances/network-instance/protocols/protocol[identifier=STATIC][name=DEFAULT]/static-routes` are supported; other protocol instances are rejected.
2. Only the leaves listed in the [Scope](#scope) YANG tree are supported; attributes such as `set-tag`, `metric`, `recurse`, `preference`, and BFD timing parameters are not supported.
3. BFD is limited to the `enable-bfd/config/enabled` leaf on IP next-hops.
4. Blackhole routes use OpenConfig `next-hop=DROP`; CONFIG_DB stores the no-gateway address (`0.0.0.0` or `::`) and `ifname=Null0`, not the literal string `DROP`.
5. For LOCAL_LINK, OpenConfig `next-hop=LOCAL_LINK`; CONFIG_DB stores `0.0.0.0` (IPv4) or `::` (IPv6) in `nexthop` with `ifname` set to the referenced interface.
6. Prefix must be supplied in normalized CIDR form; the implementation does not auto-normalize user input.
7. PUT on a static route performs REPLACE semantics for the next-hop list. A PUT payload without `nh-network-instance` clears any existing `nexthop-vrf` value for that route.
8. DELETE on the `next-hops` container is rejected. DELETE of the only remaining next-hop is rejected; delete the entire static route prefix instead.
9. `nh-network-instance=mgmt` requires management VRF to be enabled on the device.
10. Subinterface in `interface-ref` is encoded in CONFIG_DB as `{interface}.{subinterface}` in the aligned `ifname` CSV entry.
11. Next-hop list key `index` values:

| Next-hop type | OpenConfig `config/next-hop` | OpenConfig list key `index` |
|---------------|------------------------------|----------------------------|
| IP only | `{ip}` | `{ip}` |
| DROP / blackhole | `DROP` | `DROP` |
| Interface only (LOCAL_LINK) | `LOCAL_LINK` | `LOCAL_LINK+{interface}` |
| LOCAL_LINK + subinterface | `LOCAL_LINK` | `LOCAL_LINK+{interface}.{subif}` |
| IP + interface | `{ip}` | `{ip}+{interface}` |
| IP + interface + subinterface | `{ip}` | `{ip}+{interface}.{subif}` |

# 5 Error Handling
Invalid configurations and unsupported operations will report an error.

# 6 Unit Test cases
## 6.1 Functional Test Cases
1. Create, verify, and delete Static Routes using PUT, PATCH, POST, GET, and DELETE via REST/gNMI.
2. Verify GET, PATCH, PUT, POST and DELETE for IPv4 static routes with IP next-hop works as expected via REST/gNMI.
3. Verify GET, PATCH, PUT, POST and DELETE for IPv6 static routes with LOCAL_LINK interface next-hop works as expected via REST/gNMI.
4. Verify GET, PATCH, PUT, and DELETE for static routes with DROP next-hop works as expected via REST/gNMI.
5. Verify GET, PATCH, PUT, and DELETE for BFD configuration on IP next-hops works as expected via REST/gNMI.
6. Verify multiple next-hops per static route configuration works as expected via REST/gNMI.
7. Verify gNMI subscription for static route prefix config and next-hops works as expected.
8. Verify static route configuration with different interface types (Ethernet, PortChannel, Loopback).
9. Verify `nh-network-instance` (nexthop VRF) configuration including `default` and `mgmt` works as expected via REST/gNMI.
10. Verify PUT REPLACE clears omitted `nh-network-instance` from CONFIG_DB.

## 6.2 Negative Test Cases
1. Verify GET after DELETE returns a "Resource Not Found" error.
2. Verify invalid or non-normalized prefix format returns appropriate error.
3. Verify invalid next-hop IP address returns appropriate error.
4. Verify non-existent interface reference returns appropriate error.
5. Verify DELETE of the only next-hop returns appropriate error.
6. Verify DELETE of the next-hops container returns appropriate error.
7. Verify BFD with DROP next-hop on REPLACE returns appropriate error.
