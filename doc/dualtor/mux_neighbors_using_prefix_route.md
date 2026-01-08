# Prefix based Mux Neighbors
Prefix based mux neighbors is an optimization of mux neighbors for dual ToR topology to reduce time complexity and improve system performance during mux state transitions.

<!-- TOC orderedlist:true -->

## Table of Content
- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
  - [5.1 SONiC Requirements](#51-sonic-requirements)
  - [5.2 ASIC Requirements](#52-asic-requirements)
- [6. Prefix Based Mux Neighbor Architecture](#6-prefix-based-mux-neighbor-architecture)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Orchagent](#71-orchagent)
    - [7.1.1 NeighborOrch](#711-neighbororch)
    - [7.1.2 MuxOrch](#712-muxorch)
    - [7.1.3 Mux Mode Config Handling](#713-mux-mode-config-handling)
    - [7.1.4 Flow Diagram and Orch Components](#713-flow-diagram-and-orch-components)
  - [7.2 DB Schema Changes](#72-db-schema-changes)
    - [7.2.1 Config-DB](#721-config-db)
    - [7.2.2 State-DB](#722-state-db)
  - [7.3 Utilities](#73-utilities)
    - [7.3.1 Dualtor neighbor check](#731-dualtor-neighbor-check)
- [8. Warm Reboot Support](#8-warm-reboot-support)

<!-- /TOC -->

### 1. Revision

|  Rev  |   Date   |         Author       | Change Description             |
| :---: | :------: | :------------------: | ------------------------------ |
|  0.1  | 12/19/25 |  Manas Kumar Mandal  | Initial version                |

### 2. Scope
This document provides the high level design of prefix based Mux neighbors.

### 3. Definitions/Abbreviations

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| NPU | Network Processing Unit - ASIC used for processing and forwarding packets |
| ToR | Top of Rack Switch that connects to the servers on the rack |

### 4. Overview
Prefix based mux neighbors is an optimization in orchagent to reduce the complexity of mux state transitions by eliminating the need for neighbor entry add/remove operations. Instead of creating and deleting neighbor entries during mux state changes, a persistent neighbor entry is created with a separate prefix route that can be dynamically updated to point to either the direct neighbor nexthop or a tunnel nexthop. This approach simplifies the state transition process, reduces overhead, and improves time complexity while maintaining the same traffic forwarding behavior.

### 5. Requirements
#### 5.1 SONiC Requirements
SONiC needs to be enhanced to support prefix based mux neighbors with following changes:
* **Neighbor Creation**: Modify the neighbor creation process to identify mux neighbors and set the `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute to true when platform is capable, preventing implicit host route creation.
* **Prefix Route Management**: Implement logic to create and manage separate prefix routes for mux neighbors, allowing dynamic updates of the nexthop based on mux state. This will allow muxorch to make state transtion logic simpler and efficient by updating the mux state transition logic to modify the prefix route's nexthop instead of adding/removing neighbor entries in SAI.
* **Capability Check**: Implement a capability check during initialization to determine if the underlying ASIC supports the `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute. In absence of support, SONiC should revert to the host_route mux neighbor approach.
* **Backward compatibility**: Support backward compatibility using a config knob to force back to host_route mux neighbor programming irrespective of the platform's capability. Mux ports can individually be configured to use prefix based mux neighbors or host_route mux neighbors based on platform capability and config flag. Dynamic changes to neighbor mode need not be supported. 

#### 5.2 ASIC Requirements
Prefix based mux neighbors rely on support of `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute in SAI neighbor object, so the underlying ASIC must support this attribute to use this enhancement. When this attribute is not supported by the underlying ASIC, SONiC will fall back to host_route mux neighbor approach keeping backward compatibility for the platforms which do not support this feature.

### 6. Prefix Based Mux Neighbor Architecture
This feature involves changing the way mux neighbor entries are created and managed in SONiC. In the traditional approach, adding a neighbor involved creating a SAI neighbor and a nexthop, which implicitly creates a host route (/32 for IPv4, /128 for IPv6) that points directly to the neighbor nexthop. This implicit host route is not a SAI route object that can be reprogrammed or controlled by SONiC. With prefix-based mux neighbors this changes as follows:

* **Neighbor Entry**: The neighbor entry is created with `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE=true`, which prevents implicit host route creation in SDK/ASIC.
* **Separate Prefix Route**: A separate /32 (IPv4) or /128 (IPv6) prefix route is explicitly created that points to the neighbor as its nexthop.
* **Nexthop Flexibility**: The prefix route's nexthop can be dynamically updated between:
  - **Direct neighbor nexthop**: Points directly to the neighbor entry (active state)
  - **Tunnel nexthop**: Points to the IPinIP tunnel nexthop (standby state)

Following SAI forwarding pipeline diagrams illustrate the difference between host_route mux neighbor and prefix based mux neighbor.

**Host Route Mux Neighbor:**
Notice how a host route is created implicitly with host_route mux neighbor in the diagram below.
<div align="center"> <img src=./image/Host_Route_Nbr.png width=750 /> </div>

**Prefix Based Mux Neighbor:**
Notice in case of no host route an explitcit prefix route is created for the prefix based mux neighbor in the diagram below.
<div align="center"> <img src=./image/No_Host_route_nbr.png width=950 /> </div>

### 7. High-Level Design
To support prefix based mux neighbors changes will be limited to Orchagent, DB schema, and utility functions.

#### 7.1 Orchagent
Orchagent will be enhanced to support prefix based mux neighbors.

##### 7.1.1 NeighborOrch
NeighborOrch's neighbor creation and deletion logic will be modified to support prefix based mux neighbors.
NeighborOrch will be enhanced to support creation of mux neighbors with `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute when platform is capable and config flag is not disabled. The following changes will be made:
* During neighbor creation, check if the neighbor is a mux port neighbor.
* If it is a mux port neighbor with prefix based mux neighbor setting and platform is capable, set the `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute to true.  This will make sure the neighbor entry created without an implicit host route.
* Create a separate prefix route (server_ip/32 or server_ipv6/128) with the neighbor nexthop as the initial nexthop depending on the state of the mux port.

##### 7.1.2 MuxOrch
Currently MuxOrch has a single flavor of neighbor handler, with this enhancement it will introduce a prefix based mux neighbor handler. MuxOrch will create neighbor handlers based on platform capability and config flag of each mux port. This will allow coexistence of both host_route mux neighbors and prefix based mux neighbors in the same system. MuxOrch will update the  new field `neighbor_mode` of MUX_CABLE_TABLE schema in State-DB to indicate if the mux port is using prefix based mux neighbors.
MuxOrch will listen to state changes from linkmgrd and does the following at a high-level:
* Update neighbor prefix routes with neighbor nexthop or tunnel nexthop.

* **During active to standby transition**: The prefix route's nexthop is updated from the direct neighbor nexthop to the tunnel nexthop, redirecting traffic through the IPinIP tunnel to the peer ToR.
* **During standby to active transition**: The prefix route's nexthop is updated from the tunnel nexthop back to the direct neighbor nexthop, allowing direct traffic forwarding to the server.
* The neighbor entry itself remains persistent throughout state transitions, improving stability and performance.
* A port can be configured as mux port after learning the neighbor entry. In this case, neighbororch will expose API for MuxOrch to convert this neighbor to a mux neighbor by setting the `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` attribute and creating the prefix route.

**Traffic Forwarding Behavior:**
* **Active State**: Server traffic flows: `Incoming packet → Prefix route lookup → Direct neighbor nexthop → Server`
* **Standby State**: Server traffic flows: `Incoming packet → Prefix route lookup → Tunnel nexthop → IPinIP tunnel → Peer ToR → Server`

#### 7.1.3 Mux Mode Config Handling
The new config `neighbor_mode` in the MUX_CABLE table of Config-DB will allow users to configure mux ports to use either host_route mux neighbors or prefix based mux neighbors. The default mode is chosen to be `prefix_route` to enable prefix based mux neighbors in platform that support no_host_route neighbor attribute as default behavior. If the platform does not support prefix based mux neighbors, SONiC will fall back to host_route mux neighbors to maintain backward compatibility.
A per port configuration for neighbor_mode keeps the design simple and allows comparing this new feature with traditional host_route mode while debugging issues on the same switch. This design choice also avoids multiple table definition and synchronization complexity that would arise with a global config flag.

#### 7.1.4 Flow Diagram and Orch Components
The following diagram illustrates the high-level flow of prefix based mux neighbor handling in Orchagent:
  ![tunnel](./image/orchagent.png)

#### 7.2 DB Schema Changes
##### 7.2.1 Config-DB
* New field `neighbor_mode` in `MUX_CABLE` table to determine neighbor type
```
MUX_CABLE|PORTNAME:
  neighbor_mode: host_route|prefix_route  // New field to enable/disable prefix based mux neighbors, default is prefix_route
```

##### 7.2.2 State-DB
* New field `neighbor_mode` in `MUX_CABLE_TABLE` table in State-DB will be added to indicate the type of neighbor used by the mux port.
```
MUX_CABLE_TABLE:PORTNAME:
  neighbor_mode: host_route|prefix_route  // New field indicating mux neighbor type
```

#### 7.3 Utilities
##### 7.3.1 Dualtor neighbor check
A utility function will be added to check if a given mux neighbor is using prefix based mux neighbor approach by checking the State-DB MUX_CABLE_TABLE schema for the `neighbor_mode` field.
The neighbor entry is persistent when using prefix based mux neighbor and is not deleted during mux state transitions; the dualtor_neighbor_check utility will be updated to account for this behavior when validating neighbor entries.
A new output will be introduced in the dualtor_neighbor_check utility for prefix based mux neighbors to indicate the current state of the prefix route's nexthop (direct neighbor or tunnel) as follows:
```
NEIGHBOR      MAC                PORT         MUX_STATE    IN_MUX_TOGGLE    NEIGHBOR_IN_ASIC    PREFIX_ROUTE    NEXTHOP_TYPE     HWSTATUS
------------  -----------------  -----------  -----------  ---------------  ------------------  -------------   --------------  ----------
192.168.0.3   e2:67:e4:05:9a:ec  Ethernet0    standby      no               yes                 yes             TUNNEL          consistent
192.168.0.7   9a:41:63:4f:86:7c  Ethernet16   active       no               yes                 yes             NEIGHBOR        consistent
```
For  host_route mux neighbors, the existing output format will be retained as follows:
```
NEIGHBOR      MAC                PORT         MUX_STATE    IN_MUX_TOGGLE    NEIGHBOR_IN_ASIC    TUNNEL_IN_ASIC    HWSTATUS
------------  -----------------  -----------  -----------  ---------------  ------------------  ----------------  ----------
192.168.0.9   fe:5b:87:84:a8:81  Ethernet24   active       no               yes                 no                consistent
192.168.0.11  f6:56:ef:ae:8b:c3  Ethernet32   standby      no               no                  yes               consistent
```
## 8 Warm Reboot Support
TBD

