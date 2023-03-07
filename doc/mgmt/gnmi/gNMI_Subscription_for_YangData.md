# gNMI Subscription for YANG Data

This document describes the high level design for SONiC Telemetry service and Translib infrastructure
to support gNMI subscriptions and wildcard paths for YANG defined paths.

## Table of Contents

## Revision History

| Rev |     Date    |       Author       | Change Description                                     |
|-----|-------------|--------------------|--------------------------------------------------------|
| 0.1 | 03/02/2023  | Sachin Holla       | Initial draft                                          |

## Definition and Abbreviation

| **Term**       | **Meaning**                         |
|----------------|-------------------------------------|
| gNMI           | gRPC Network Management Interface   |
| gRPC           | gRPC Remote Procedure Call (it is a recursive acronym!!)   |
| YGOT           | [YANG Go Tools](https://github.com/openconfig/ygot); a Golang library to process YANG data |

## 1 Feature Overview

### 1.1 Introduction

### 1.2 Requirements

#### 1.2.1 ON_CHANGE subscription for eligible paths

Infrastructure should support ON_CHANGE subscription for YANG paths based on redis keyspace notifications.
It should provide APIs for apps to specify ON_CHANGE unsupported paths.
An `INVALID_ARGUMENT` status should be returned if the target path or any of its descendent paths do not support ON_CHANGE.

#### 1.2.2 SAMPLE subscription for all paths

Infrastructure should support SAMPLE subscription for all YANG paths.
It should provide APIs for apps to indicate minimum `sample_interval` supported for the path.
An `INVALID_ARGUMENT` status should be returned if the minimum `sample_interval` of target path or any of its descendent paths is more than the requested `sample_interval`.

#### 1.2.3 TARGET_DEFINED subscription for all paths

Infrastructure should support TARGET_DEFINED subscription for all YANG paths.
Subscribe request should be treated as ON_CHANGE or SAMPLE based on the app's preferences for the target path.
It should split into multiple requests if the target path supports ON_CHANGE
but some of its descendent paths do not.

#### 1.2.4 POLL and ONCE subscriptions

Infrastructure should support SAMPLE subscription for all YANG paths.

#### 1.2.5 Support Wildcard Keys

Infrastructure should support wild cards in **path key** for all subscription modes.
Example: `/openconfig-interfaces:interfaces/interface[name=*]/config`.
Path can contain any number of wildcard key values.
Apps should be allowed to indicate wildcard unsupported paths.
An `INVALID_ARGUMENT` status should be returned if wildcard key cannot be supported for the target path.

Wildcard in path element (like `/interfaces/*/config` or `/interfaces/.../config`) is a stretch goal.

#### 1.2.6 Scalar encoding for telemetry updates

All telemetry updates should be encoded as gNMI scalar types.
Each update entry should be a {leaf path, scalar value} pair.
Scalar type encoding is explained in gNMI specification [section 2.2.3](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md#223-node-values).

### 1.3 References

SONiC Management Framework<br>
https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md

SONiC gNMI Server Interface Design<br>
https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/gnmi/SONiC_GNMI_Server_Interface_Design.md

gNMI Specification<br>
https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md

gNMI Protobuf Definition<br>
https://github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto

## 2 High Level Design

## 3 Design Details

### 3.1 Translib APIs

### 3.2 App Interface

### 3.3 Transformer

### 3.4 gNMI Server

## 4 User Interface

### 4.1 CLIs

No CLIs will be added or modified.

### 4.1 gNOI APIs

## 5 Serviceability and Debug

## 6 Scale Considerations

SAMPLE, ON_CHANGE, TARGET_DEFINED are long running subscriptions and they maintain a data cache per session.
Cache size is not deterministic; it depends on number of clients and the subscribed paths.
E.g, If clients subscribe for specific leaf nodes (like `/interfaces/interface[name=*]/state/oper-status`), the cache would hold only that leaf related data (or DB entry in case of ON_CHANGE).
But if clients subscribe for top level YANG containers/lists (like `/interfaces/interface[name=*]`) the cache would hold information for the entire data tree.
This can drastically increase the memory consumption of telemetry service.
But the exact numbers depend on the implementation and we do not have a correct estimate at this point.

CPU consumption telemetry service can also increase if the DB entries monitored through ON_CHANGE subscriptions change frequently.
E,g. interface counters.
Applications should disable ON_CHANGE for such YANG paths.

gNMI server can also throttle the subscription requests based on the current device state.
It can close the subscribe RPC with RESOURCE_EXHAUSTED status if it is oversubscribed.
Such throttling mechanism should also consider the platform capabilities.
This can be explored in future releases.

## 7 Limitations

- ON_CHANGE can be supported for YANG nodes that are mapped to DB tables only
- Wildcard keys in subscribe paths can be supported for YANG nodes that are mapped to DB tables only
- Subscribe not supported for paths with wildcard element names.
  Only wildcard keys are allowed.
- Wildcard paths not supported in gNMI Get RPC.

## 8 Unit Tests

Following unit test cases require app code changes to handle subscription.
Test YANGs will be used to simulate these conditions.
Each test will cover value create/update/delete cases wherever possible.

ON_CHANGE test cases:

- ON_CHANGE subscription for top level container path
- ON_CHANGE subscription for list node with wildcard key
- ON_CHANGE subscription for list node with specific key
- ON_CHANGE subscription for list node with specific, but non-existing key
- ON_CHANGE subscription for nested list node with wildcard key
- ON_CHANGE subscription for nested list node with specific key
- ON_CHANGE subscription for top level leaf nodes (without any keys)
- ON_CHANGE subscription for container inside a list
- ON_CHANGE subscription for leaf node inside a list, with an initial value
- ON_CHANGE subscription for leaf node inside a list, value does not exits
- ON_CHANGE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- ON_CHANGE subscription for leaf-list node inside a list; with leaf-list mapped to its own DB entry
- ON_CHANGE subscription for an unsupported path - for non-transformer app
- ON_CHANGE subscription for an unsupported path - marked through transformer annotation
- ON_CHANGE subscription for an unsupported path - marked through subtree transformer code
- ON_CHANGE subscription for a non-DB path
- ON_CHANGE subscription with unknown path
- ON_CHANGE subscription with `updates_only` set to true

SAMPLE subscription test cases:

- SAMPLE subscription for top level container path
- SAMPLE subscription for list node with wildcard key
- SAMPLE subscription for list node with specific key
- SAMPLE subscription for nested list node with wildcard key
- SAMPLE subscription for nested list node with specific key
- SAMPLE subscription for top level leaf nodes (without any keys)
- SAMPLE subscription for container inside a list
- SAMPLE subscription for leaf node inside a list
- SAMPLE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- SAMPLE subscription for leaf-list node inside a list; with leaf-list mapped to its own DB entry
- SAMPLE subscription for a non-DB path, with wildcard keys
- SAMPLE subscription for a non-DB path, without wildcard keys
- SAMPLE subscription with unknown path
- SAMPLE subscription with sample_interval less than min interval supported by YANG
- SAMPLE subscription with `suppress_redundant` set to true
- SAMPLE subscription with `updates_only` set to true.
- Both ON_CHANGE and SAMPLE subscriptions in a single request.

TARGET_DEFINED subscription test cases:

- TARGET_DEFINED for a node that prefers ON_CHANGE
- TARGET_DEFINED for a node that prefers SAMPLE -- preference set through transformer annotation
- TARGET_DEFINED for a node that prefers SAMPLE -- preference set through subtree transformer
- TARGET_DEFINED for a node that prefers SAMPLE -- for non-transformer app
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- preference set through transformer annotation
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- preference set through subtree transformer
- TARGET_DEFINED for a node that prefers ON_CHANGE, but a child node prefers SAMPLE -- for non-transformer app
- TARGET_DEFINED for non-DB path
- TARGET_DEFINED for unknown path

ONCE subscription test cases:

- ONCE subscription for top level container path
- ONCE subscription for list node with wildcard key
- ONCE subscription for list node with specific key
- ONCE subscription for top level leaf nodes (without any keys)
- ONCE subscription for container inside a list
- ONCE subscription for leaf node inside a list
- ONCE subscription for leaf-list node inside a list; with leaf-list mapped to a DB field
- ONCE subscription for a non-DB path, with wildcard keys
- ONCE subscription for a non-DB path, without wildcard keys
- ONCE subscription with unknown path

GetSubscribePreferences gNOI API:

- Get preferences for a container path that supports ON_CHANGE and all its subpaths also support ON_CHANGE
- Get preferences for a container path that supports ON_CHANGE but some of its child paths do not
- Get preferences for a path that do not support ON_CHANGE
- Get preferences for a leaf path (with and without ON_CHANGE support)
- Get preferences for multiple paths
- Get preferences with include_subpaths=true
- Get preferences with on_change_supported filter (both TRUE and FALSE)
- Get preferences for a non-db path
- Get preferences without wildcard keys and without module prefixes
- Check error response for an invalid path
- Send request and close the client stream immediately (manual verification of server logs)
- Send request and close the channel immediately (manual verification of server logs)
