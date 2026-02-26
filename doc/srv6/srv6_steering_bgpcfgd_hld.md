# Bgpcfgd SRv6 Traffic Steering Configuration

# Table of Contents

- [Bgpcfgd SRv6 Traffic Steering Configuration](#bgpcfgd-srv6-traffic-steering-configuration)
- [Table of Contents](#table-of-contents)
- [Revision](#revision)
- [Definition/Abbreviation](#definitionabbreviation)
    - [Table 1: Abbreviations](#table-1-abbreviations)
- [1 Introduction and Scope](#1-introduction-and-scope)
- [2 Feature Requirements](#2-feature-requirements)
- [3 Feature Design](#3-feature-design)
  - [3.1 ConfigDB Changes](#31-configdb-changes)
  - [3.2 Bgpcfgd Changes](#32-bgpcfgd-changes)
  - [3.3 frrcfgd Changes](#33-frrcfgd-changes)
  - [3.4 YANG Model](#34-yang-model)
- [4 Unit Tests](#4-unit-tests)
- [5 System Tests](#5-system-tests)

# Revision

| Rev  |   Date    |           Author           | Change Description      |
| :--: | :-------: | :------------------------: | :--------------------- |
| 0.1  | 02/19/2026 | Carmine Scarpitta, Ahmed Abdelsalam | Initial version        |

# Definition/Abbreviation

### Table 1: Abbreviations

| ****Term**** | ****Meaning**** |
| -------- | ----------------------------------------- |
| FRR | Free Range Routing - open source routing software |
| SID | Segment Identifier |
| SIDlist | Segment list - ordered sequence of SIDs |
| SRv6 | Segment Routing IPv6 |
| VRF | Virtual Routing and Forwarding |
| bgpcfgd | BGP configuration daemon in SONiC |
| frrcfgd | FRR configuration daemon in SONiC |


# 1 Introduction and Scope

SONiC supports SRv6 traffic steering. It can be currently configured using the FRR CLI.

This document describes adding SRv6 traffic steering configuration support in bgpcfgd and frrcfgd.

# 2 Feature Requirements

Provide the ability to configure SRv6 traffic steering from CONFIG_DB.

# 3 Feature Design

This section describes the CONFIG_DB, bgpcfgd, and frrcfgd changes needed to add SRv6 traffic steering configuration support.

## 3.1 ConfigDB Changes

**STATIC_ROUTE Table**

CONFIG_DB includes the STATIC_ROUTE table for static route configuration.

We extend the STATIC_ROUTE table by adding a `sidlist` field to enable static routes to be steered over SRv6 SID lists:

```diff
  key = STATIC_ROUTE|vrf-name|prefix

  ; field = value
  nexthop = string               ; list of gateway addresses for traffic steering
  ifname = string                ; list of interfaces
  distance = string              ; list of distances (metric)
  nexthop-vrf = string           ; list of next-hop VRFs for route leaks
  blackhole = string             ; list of booleans for blackhole routes
+ sidlist = string               ; SRv6 SID list for traffic steering
```

These changes align with the APPL_DB schema defined in [srv6_hld.md](https://github.com/sonic-net/SONiC/blob/master/doc/srv6/srv6_hld.md).

The following examples demonstrate how to configure a static route with a SID list:

```
Example: IPv4 route over a SID list in the default VRF
    "STATIC_ROUTE": {
        "default|10.0.0.0/24": {
            "ifname": "Ethernet0",
            "sidlist": "FCBB:BBBB:2:3:FEDD::"
        }
    }

Example: IPv6 route over a SID list in a non-default VRF
    "STATIC_ROUTE": {
        "VrfA|2001:db8:10::/64": {
            "ifname": "Ethernet4",
            "sidlist": "FCBB:BBBB:4:5:6:FEDD::"
        }
    }
```

## 3.2 Bgpcfgd Changes

bgpcfgd includes a component called **StaticRouteManager** that monitors STATIC_ROUTE table updates and translates static route entries into FRR configuration.

We extend **StaticRouteManager** to process the new `sidlist` field, parsing it and propagating it to FRR.

bgpcfgd validates all CONFIG_DB entries. Invalid entries are logged to syslog and are not applied to FRR.

The following example shows how StaticRouteManager translates CONFIG_DB entries into FRR configuration. It configures two STATIC_ROUTE entries in CONFIG_DB with SID lists for SRv6 traffic steering:

```
"STATIC_ROUTE": {
    "default|10.0.0.0/24": {
        "ifname": "Ethernet0",
        "sidlist": "FCBB:BBBB:2:3:FEDD::"
    },
    "default|2001:db8:10::/64": {
        "ifname": "Ethernet4",
        "sidlist": "FCBB:BBBB:4:5:6:FEDD::"
    }
}
```

When bgpcfgd processes these CONFIG_DB entries, StaticRouteManager translates them into the corresponding FRR command syntax. The resulting FRR configuration is:

```
ip route 10.0.0.0/24 Ethernet0 segments fcbb:bbbb:2:3:fedd:: encap-behavior H_Encaps_Red
ipv6 route 2001:db8:10::/64 Ethernet4 segments fcbb:bbbb:4:5:6:fedd:: encap-behavior H_Encaps_Red
```

FRR then programs these routes into the SONiC data plane, which encapsulates matching packets with the specified SID lists before forwarding them to the destination.

## 3.3 frrcfgd Changes

In addition to bgpcfgd changes, we extend the frrcfgd static route handler to process the `sidlist` field in the `STATIC_ROUTE` table.

Specifically, frrcfgd reads and validates the `sidlist` field in `STATIC_ROUTE` entries, carries it through static route processing, and generates the corresponding SRv6 static route configuration in FRR. The generated FRR syntax is the same as the one shown in [Section 3.2 Bgpcfgd Changes](#32-bgpcfgd-changes).

## 3.4 YANG Model

This section describes the YANG model extensions required to support SRv6 traffic steering configuration.

The sonic-static-route YANG model is extended to include `sidlist` as a structured list under `STATIC_ROUTE_LIST`. The updated model is shown below:

```
  module: sonic-static-route
    +--rw sonic-static-route
        +--rw STATIC_ROUTE
            +--rw STATIC_ROUTE_LIST* [vrf_name prefix]
                +--rw vrf_name       union
                +--rw prefix         inet:ip-prefix
                +--rw nexthop?       string
                +--rw ifname?        string
                +--rw advertise?     string
                +--rw distance?      string
                +--rw nexthop-vrf?   string
                +--rw blackhole?     string
+               +--rw sidlist* [name]
+                   +--rw name    string
+                   +--rw sid*    inet:ipv6-address
```

Refer to [sonic-yang-models](https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-yang-models) for the YANG model defined with standard IETF syntax.

# 4 Unit Tests

Unit tests validate that bgpcfgd/frrcfgd correctly translate CONFIG_DB entries into FRR configuration.

| Test Cases | Test Result |
| :------ | :----- |
| add IPv4 static route with sidlist in CONFIG_DB | verify the static route config entry with SID list is created in FRR config |
| delete IPv4 static route with sidlist in CONFIG_DB | verify the static route config entry with SID list is removed from FRR config |
| add IPv6 static route with sidlist in CONFIG_DB | verify the static route config entry with SID list is created in FRR config |
| delete IPv6 static route with sidlist in CONFIG_DB | verify the static route config entry with SID list is removed from FRR config |

# 5 System Tests

System tests verify end-to-end functionality for SRv6 traffic steering across CONFIG_DB, FRR, and the data plane.

| Test Case | Description |
| :------ | :----- |
| IPv4 with sidlist (config) | Configure IPv4 static route with sidlist and verify SID list and route entry in APPL_DB |
| IPv6 with sidlist (config) | Configure IPv6 static route with sidlist and verify SID list and route entry in APPL_DB |
| IPv4 with sidlist (dataplane) | Configure IPv4 static route with sidlist and verify dataplane steering |
| IPv6 with sidlist (dataplane) | Configure IPv6 static route with sidlist and verify dataplane steering |
