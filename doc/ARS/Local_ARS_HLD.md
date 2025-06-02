# Local ARS HLD #

## Table of Content 

- [Revision](#revision)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Scope](#scope)
- [Overview](#overview)
- [Use cases](#use-cases)
- [Requirements](#requirements)
- [Architecture Design](#architecture-design)
- [High Level Design](#high-level-design)
- [Sequence diagrams](#sequence-diagrams)
  - [Initialization Flow](#figure-4-initilization-flow)
  - [Interface Update Flow](#figure-5-interface-update-flow)
  - [Nexthop group table created by RouteOrch flow](#figure-6-nexthop-group-table-created-by-routeorch-flow)
  - [Nexthop group table created by NhgOrch flow](#figure-7-nexthop-group-table-created-by-nhgorch-flow)
  - [ARS LAG Table Creation Flow](#figure-8-ars-lag-table-creation-flow)
  - [LAG Table Creation Flow](#figure-9-lag-creation-flow)
  - [LAG Member Addition Flow](#figure-10-lag-member-addition-flow)
  - [ACL Configuration Flow](#figure-11-acl-configuration-flow)
- [SAI API](#sai-api)
- [CLI/YANG model Enhancements](#configuration-and-management)
- [Yang mode Enchancements](#yang-model-enhancements)
  - [ARS_PROFILE table](#ars_profile)
  - [ARS_INTERFACES table](#ars_interface)
  - [ARS_PORTCHANNELS table](#ars_portchannel)
  - [ARS_NEXTHOP_GROUP table](#ars_nexthop_group)
  - [ARS_NEXTHOP_MEMBER table](#ars_nexthop_group_member)
  - [ARS_PORTCHANNEL table](#ars_portchannel)
  - [ACL_RULE table](#acl_rule)
- [Config DB Enhancement](#config-db-enhancements)
- [State Db Enhancement](#state-db-enhancements)
- [Counters](#counters)
- [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
- [Restrictions/Limitations](#restrictionslimitations)
- [Unit Test cases](#unit-test-cases)
- [System Test cases](#system-test-cases)

### Revision  

| Revision | Date        | Author                    | Change Description            |
| -------- | ----------- | ------------------------- | ----------------------------- |
| 1.0      | Dec 01 2024 | Vladimir Kuk              | Initial proposal              |
| 1.1      | Apr 21 2025 | Vladimir Kuk              | Review comments update        |
| 1.2      | May 12 2025 | Vladimir Kuk              | Addressing community comments |
| 1.3      | May 28 2025 | Ashok Kumar/Gnana Priya   | Addressing community comments |

### Definitions/Abbreviations 

| Definitions/Abbreviation | Description |
| ------------------------ | ----------- |
| ARS  | Adaptive Routing and Switching  |
| NHG  | Nexthop Group                   |
| ECMP | Equal Cost MultiPath            |
| LAG  | Link Aggregation Group          |
| ACL  | Access Control List             |
| SAI  | Switch Abstraction Interface    |
| VRF  | Virtual Routing and Forwarding  |

### Scope

This high-level design document describes the implementation for Local ARS in SONiC.

### Overview 

**Existing Forwarding Decision Model**

Today, routing protocols or SDN controllers establish destination reachability and compute all possible paths, whether equal-cost or unequal-cost. However, the selection of a specific path from the available ECMP paths is performed statically in the switch data plane, driven by a hash computed over packet header fields. This static hashing mechanism does not account for real-time path conditions of the local or end-to-end path, as a result, once a path is chosen, the packet flow remains locked to that path, leading to inefficient load balancing and potential network hotspots.
Control plane protocols exist for traffic engineering paths, but involves control plane decisions that are very slow to react to changing traffic patterns in the network or state of interfaces.

Adaptive Routing and Switching (ARS) allows dynamic selections of the best available path for data packets based on real-time network conditions. This approach helps to mitigate congestion, optimize resource utilization, and improve overall network performance.

No standard exists, but there is an industry consensus for general approach.

ARS can be divided into two parts:
- Local ARS - Scope of this HLD, focuses on dynamic path selection within a single device. It enables more granular control over routing decisions by considering the real-time utilization of local egress ports. This is achieved by monitoring local port utilization, identifying micro flows inside of incoming macro flow and assigning best available path.
- Global ARS - focuses on selecting non-congested path to end host by exchanging ports utilization data, between remote devices.

This design follows SAI conceptual model described in https://github.com/opencomputeproject/SAI/blob/master/doc/ARS/Adaptive-Routing-and-Switching.md.

The diagram illustrates a Conceptual Packet Flow, where macro flows are collections of multiple micro flows. Micro flows, identified by a 5-tuple (source IP, destination IP, protocol, source port, destination port), are hashed, and if several micro flows hash to the same bucket, they are grouped into a macro flow. These flows are further segmented into flow-lets based on idle time thresholds between packets. A Macro Flow Table maps these flows to next-hop destinations and tracks their status (e.g., "active" or "expired"). Using Adaptive Routing within an ECMP group, the system dynamically assigns traffic based on link quality metrics like latency and packet loss.

__Figure 1: ARS Packet Flow__
![ARS flow](images/ARSPacketFlow.png "Figure 1: ARS Packet Flow")
This diagram outlines a Logical Pipeline Flow for Adaptive Routing with ARS. Flow starts with L3 Route Lookup to identify the appropriate Next-Hop Group (NHG). If ARS is enabled, the system generates an ARS Macro Flow ID and assigns packets to specific next-hop destinations using a Macro Flow Table. Otherwise, traffic undergoes standard ECMP processing. In the background, ARS monitors port load metrics (past and future) and updates the Macro Flow Table using adaptive algorithms and quality thresholds to ensure optimal traffic distribution based on real-time link conditions.

__Figure 2: ARS SAI Pipeline Flow__
![SAI model](images/ARSPipeline.png "Figure 2: ARS Pipeline Flow")

### Use cases
- L3 traffic egressing via NHG
    * NH pointing to port
    * NH pointing to lag
- L2 traffic egressing via LAG
- Tunnel interface as egress interface is not supported

### Requirements

## Phase 1
    - Support different ARS modes,
          - Flowlet-based port selection
          - Per-packet port selection
    - Support path quality configuration
    - Support ACL action to disable ARS 
    - Support enabling ARS for NHGs managed by RouteOrch, 
          - Determine NHG eligibility for ARS based on ARS profile ars_nhg_mode.

## Phase 2
    - Support enabling ARS for NHGs managed by NhgOrch, 
          - Determine NHGs eligibility for ARS based on ARS profile ars_nhg_mode.
    - Support enabling ARS over LAG
    - Support Alternative path for ECMP and LAG
    - Support for Statistics

### Architecture Design 

The following orchestration agents will be added or modified. The flow diagrams are captured in a later section.

![Orchestration agents](images/config_flow.png)
###### Figure 3: Orchestration Agents

![Orchestration agents](images/orch_design.png)
###### Figure 4: Orchestration Design

#### Orchdaemon
orchdaemon - it is the main orchestration agent, which handles all Redis DB's updates, then calls appropriate orchagent, the new arsorch should be registered inside the orchdaemon.

#### ArsOrch
arsorch - it is an ARS orchestration agent that handles the configuration requests from CONFIG_DB. It is responsible for creating the SAI ARS profile and configuring SAI ARS object. 

#### RouteOrch
routeOrch monitors operations on Route related tables in APPL_DB and converts those operations in SAI commands to manage IPv4/IPv6 route, nexthops and nexthop group. New functionality for nexthop group change notification and configuring ARS-enabled NHG.

#### NhgOrch
nhgOrch monitors operations on Nexthop Group related tables in APPL_DB and converts those operations in SAI commands to optimize performance when multiple routes using same NHG. New functionality for nexthop group change notification and configuring ARS-enabled NHG.

#### PortsOrch
portsorch handles all ports-related configurations. New functionality for enabling ARS on ports.

#### AclOrch
aclorch is responsible for managing the configurations of ACL table and ACL rules. New ACL rule action for controlling ARS operation.

```
ARS is closely tied to vendor-specific hardware implementations, requiring thorough validation of all configurations
(apis and attributes) using SAI capabilities.
```

### High-Level Design 

ARS configuration consists of creating an ARS profile and enabling ARS on the designated ports. This process also includes activating ARS for nexthop groups (Adaptive Routing) and LAGs (Adaptive Switching). At present, configurations are carried out statically via CONFIG_DB, with potential future enhancements to incorporate management through an external controller or routing protocol extensions.

- A New OrchAgent module, ArsOrch, is introduced to orchestrate ARS-related functionalities such as,
     - Support for ARS profile 
     - Support ARS over nexthop groups
     - Enable/Disable interfaces for ARS
     - Support nexthop members config for ARS nexthop group selection
     - Support ARS over portchannel groups
     - Enable/Disable portchannels for ARS portchannel groups
     - Allow configuration of path metrics

- ACL changes<br>
When a new ACL table is created, SAI needs to receive a list of supported actions that can be allowed to rules within that table.
To enable support for the new ARS disable action, the custom table type schema will be extended to include a new action attribute 
- "DISABLE_ARS_FORWARDING" as part of the actions attribute field.

**Table interactions**:

1. ARS_PROFILE defines the ARS global configuration parameters. ArsOrch uses this to create the ARS profile in SAI. 
   Currently, only a single profile is supported. If multiple profiles are required, the SAI implementation must also be enhanced to accommodate this functionality.
 
2. ARS_NEXTHOP_GROUP table used to specify ARS nexthop group configuration parameters. ArsOrch uses this to create the L3 ARS SAI object.

3. ARS_PORTCHANNEL_GROUP table used to specify ARS lag configuration parameters. ArsOrch uses this to create the L2 ARS SAI object.

4. ARS_INTERFACES holds list of L2 interfaces which are ARS-enabled. NHG will be considered ARS-enabled when all of its associated nexthop interfaces are present in the configured ARS_INTERFACES when the match mode configured in ARS_PROFILE is interface-based.

5. ARS_NEXTHOP_MEMBER holds list of nexthops which are used for identifying ARS-enabled nexthop group. NHG will be considered ARS-enabled when all of its associated nexthops are present in the configured ARS_NEXTHOP_MEMBER entries when the match mode configured in ARS_PROFILE is nexthop-based and additionally its interface should be L2 ARS-enabled interfaces. 

6. ARS_PORTCHANNELS table hold list of lag interfaces associated with ARS_PORTCHANNEL_GROUP objects.

7. An NHG can be enabled either through the ARS_INTERFACE or the ARS_NEXTHOP_MEMBER_GROUP, both of which are user-configurable.

There are different options for NHG creation. Two modes of operation are supported:

1. NHG created by RouteOrch. APPL_DB adds entry to ROUTE_TABLE with explicit set of nexthops.

2. NHG created by NhgOrch. APPL_DB first adds an entry to the NEXTHOP_GROUP_TABLE and later adds an entry to the ROUTE_TABLE with a reference to the previously created NHG. This mode of operation will be supported only when the Nexthop group's SAI ARS object id attribute "set" capability is supported, to prevent NHG recreations when multiple routes point to the updated NHG.

The diagrams below illustrate the typical sequences for ARS configuration, showcasing key workflows for both Adaptive Routing and Adaptive Switching.


#### Sequence diagrams

##### __Figure 5: Initilization flow__
![](images/init_seq.png)

1. Bind to Events
    - Events from PortOrch
        * The ArsOrch component binds to following events to start monitoring and processing ARS-related interfaces:
            - Port operational status
            - Port change
            - Lag member change
    - Events from RouteOrch
        * The ArsOrch component binds to route updates to monitor nexthop group changes.
    - Events from NhgOrch
        * The ArsOrch component binds to nexthop group updates to monitor nexthop group changes.

2. Get ARS SAI Capabilities
    * ArsOrch retrieves ARS capabilities from the SAI layer and saves them in STATE_DB.

3. Add ARS_PROFILE Table
    * The CONFIG_DB adds the ARS_PROFILE table, which defines the ARS configuration parameters. ArsOrch uses this to create the ARS profile in SAI.

4. Add ARS_NEXTHOP_GROUP Table
    * The CONFIG_DB adds the ARS_NEXTHOP_GROUP table, which defines the ARS specific nexthop configuration parameters. ArsOrch uses this to create the ARS SAI object (logically a L3 ARS SAI object).

5. ARS_NEXTHOP_MEMBER Table
    * The CONFIG_DB adds the ARS_NEXTHOP_MEMBER table, which specifies which nexthops are used for identifying ARS nexthop group. If all of nexthops in added NHG, exist in ARS_NEXTHOP_MEMBER and are pointing to ARS-enabled L2 interface, that NHG is eligible for ARS.

6. Add ARS_INTERFACES Table
    * The CONFIG_DB adds the ARS_INTERFACE table, causing ArsOrch to enable ARS on the corresponding ports and also used for identifying ARS nexthop group.

7. Add ARS_PORTCHANNEL_GROUP Table
    * The CONFIG_DB adds the ARS_PORTCHANNEL_GROUP table, which defines the ARS specific portchannel configuration parameters. ArsOrch uses this to create the ARS SAI object (logically a L2 ARS SAI object).

8. Add ARS_PORTCHANNELS Table
    * The CONFIG_DB adds the ARS_PORTCHANNELS table, causing ArsOrch to associate LAG to ARS_PORTCHANNEL_GROUP.

##### __Figure 6: Interface update flow__
![](images/if_update.png)

1. Link UP Notification
    * The PortsOrch component detects a link state change and notifies ArsOrch when a port transitions to the "UP" state.

2. Set Port Scaling Factor
    * Based on the port's speed, PortsOrch determines the appropriate scaling factor. <br>The scaling factor is then set in the SAI layer through the syncd component to adjust the port's behavior accordingly.

##### __Figure 7: Nexthop group table created by RouteOrch flow__
![](images/nhg_create_by_ro.png)

1. Add ROUTE_TABLE Table
    * The APPL_DB adds the ROUTE_TABLE table, triggering the process.
2. Notification
    * RouteOrch component will notify ArsOrch of NHG change.
    * ArsOrch will verify that received notification matches the nexthops in ARS_NEXTHOP_MEMBER and that nexthops are defined over ARS-enabled ports
3. ARS NHG mode
    * ARS will determine whether ARS NHG mode is interface-based or nexthop-based.
        - In interface-based mode, only the interface will be matched.
        - In nexthop-based mode, both the nexthop members and the interface will be matched.
4. Nexthop group's SAI attributes handling:
    * If the "set" capability for the nexthop group's ARS object ID is supported:
        - The nexthop group is updated with the ARS object ID.
    * If "set" capability is not supported - implement via "create" functionality:
        - Create a new nexthop group with the ARS object ID.
        - Redirect existing routes to use the new nexthop group
        - Remove original nexthop group.
    * If an alternative path is defined:
        - Identify the relevant nexthops by matching them against the entries in the ARS_NEXTHOP_MEMBER table with the role set to "alternative_path."
        - Set these nexthops as part of the alternative path by updating the SAI attributes for the nexthop group or member accordingly.

##### __Figure 8: Nexthop group table created by NhgOrch flow__
![](images/nhg_create_by_nhgo.png)

1. Add NEXTHOP_GROUP_TABLE Table
    * The APPL_DB adds the NEXTHOP_GROUP_TABLE table, triggering the process.
2. Nexthop group creation
    * NhgOrch receives NHG data from APPL_DB and creates sai nexthop group.
3. Notification from NhgOrch
    * NhgOrch component notifies ArsOrch of NHG update.
4. ARS NHG mode
    * ARS will determine whether ARS NHG mode is interface-based or nexthop-based.
        - In interface-based mode, only the interface will be matched.
        - In nexthop-based mode, both the nexthop members and the interface will be matched.
5. Nexthop group's SAI attributes handling:
    * If nexthop group's ARS object ID "set" capability is supported:
        - The nexthop group is updated with the ARS object ID.
    * If "set" capability is not supported - ignore NHG update.
    * If an alternative path is defined:
        - Identify the relevant nexthops by matching them against the entries in the ARS_NEXTHOP_MEMBER table with the role set to "alternative_path."
        - Set these nexthops as part of the alternative path by updating the SAI attributes for the nexthop group or member accordingly.
6. Add ROUTE_TABLE Table
    * The APPL_DB adds the ROUTE_TABLE table, triggering the process.
7. Route creation
    * RouteOrch creates/updates route with NHG reference.
8. Notification from RouteOrch
    * RouteOrch component will notify ArsOrch of NHG update. ArsOrch will check if the NHG is implicit, meaning it was created by NhgOrch and will ignore notification

##### __Figure 9: ARS LAG Group table creation flow__
![](images/ars_lag_create.png)

1. Add ARS_PORTCHANNEL_GROUP Table
    * The CONFIG_DB adds the ARS_PORTCHANNEL_GROUP table, triggering the process.
2. Add ARS_PORTCHANNEL Table 
    * The CONFIG_DB adds the LAG associate to ARS_PORTCHANNEL_GROUP.
3. Create SAI ARS Object
    * The ArsOrch component receives the update and creates the SAI ARS object.
4. LAG's SAI attributes handling:
    * ARS checks the state of the LAG members interface's ARS capability and proceeds only if ARS is enabled.
    * If LAG was created:
        - It is updated with the ARS object ID.

##### __Figure 10: LAG creation flow__
![](images/lag_create.png)

1. LAG creation
    * PortsOrch receices LAG from APPL_DB, triggering the process.
2. Notification
    * PortsOrch component will notify ArsOrch of LAG creation.
3. LAG's SAI attributes handling:
    * LAG is updated with the ARS object ID.

##### __Figure 11: LAG member addition flow__
![](images/lag_update.png)

1. LAG change
    * PortsOrch receices LAG member from APPL_DB, triggering the process.
2. Notification
    * PortsOrch component will notify ArsOrch of LAG member change.
3. LAG's SAI attributes handling:
    * ARS checks the state of the LAG members interface's ARS capability and proceeds only if ARS is enabled.
    * If an alternative path is defined
        - Set the relevant port as part of the alternative path.

##### __Figure 12: ACL configuration flow__
![](images/acl_config.png)

1. Users define custom ACL table type in ACL_TABLE_TYPE with DISABLE_ARS_FORWARDING type.
2. ACL table added, referencing the custom table type.
3. ACL rule added, referencing ARS disable action.

### SAI API 

There are no new SAI APIs or attributes required.

Following table lists SAI usage and supported attributes with division to phase implementation:

* Phase 1

| SAI api | Supported SAI attribute 
| ------- | ----------------------- 
|create_ars_profile | SAI_ARS_PROFILE_ATTR_PORT_LOAD_PAST<br>SAI_ARS_PROFILE_ATTR_LOAD_PAST_MIN_VAL<br>SAI_ARS_PROFILE_ATTR_LOAD_PAST_MAX_VAL<br>SAI_ARS_PROFILE_ATTR_ENABLE_IPV4<br>SAI_ARS_PROFILE_ATTR_ENABLE_IPV6<br>SAI_ARS_PROFILE_ATTR_MAX_FLOWS<br>SAI_ARS_PROFILE_ATTR_ALGO<br>SAI_ARS_PROFILE_ATTR_PORT_LOAD_FUTURE<br>SAI_ARS_PROFILE_ATTR_PORT_LOAD_PAST_WEIGHT<br>SAI_ARS_PROFILE_ATTR_PORT_LOAD_FUTURE_WEIGHT<br>SAI_ARS_PROFILE_ATTR_SAMPLING_INTERVAL<br>SAI_ARS_PROFILE_ATTR_ECMP_ARS_MAX_GROUPS<br>SAI_ARS_PROFILE_ATTR_ECMP_ARS_MAX_MEMBERS_PER_GROUP
|create_ars | SAI_ARS_ATTR_MODE<br>SAI_ARS_MODE_FLOWLET_QUALITY<br>SAI_ARS_MODE_PER_PACKET_QUALITY<br>SAI_ARS_ATTR_IDLE_TIME<br>SAI_ARS_ATTR_MAX_FLOWS
|set_port_attribute|SAI_PORT_ATTR_ARS_ENABLE<br>SAI_PORT_ATTR_ARS_PORT_LOAD_SCALING_FACTOR
|create_next_hop_group|SAI_NEXT_HOP_GROUP_ATTR_ARS_OBJECT_ID
|create_acl_entry|SAI_ACL_ACTION_TYPE_DISABLE_ARS_FORWARDING

* Phase 2

| SAI api | Supported SAI attribute 
| ------- | ----------------------- 
|create_ars |SAI_ARS_ATTR_PRIMARY_PATH_QUALITY_THRESHOLD<br>SAI_ARS_ATTR_ALTERNATE_PATH_COST
|set_port_attribute|SAI_PORT_ATTR_ARS_ALTERNATE_PATH
|create_next_hop_group_member|SAI_NEXT_HOP_GROUP_MEMBER_ATTR_ARS_ALTERNATE_PATH
|set_lag_attribute|SAI_LAG_ATTR_ARS_OBJECT_ID

### Configuration and management 

#### YANG model Enhancements 

##### ARS_PROFILE

```
    container ARS_PROFILE {

        list ARS_PROFILE_LIST {

            key "profile_name";
            max-elements 1;

            leaf profile_name {
                description "ARS Profile Name";
                type string;
            }

            leaf algorithm {
                description "ARS quality algorithm";
                type enumeration {
                    enum ewma {
                        description "Exponentially Weighted Moving Average algorithm";
                    }
                }
                default "ewma";
            }

            leaf ars-nhg-mode {
                  type enumeration {
                    enum interface {
                    description "ARS NHG mode as interface based for ARS nexthop group selection.";
                    }
                    enum nexthop {
                    description "ARS NHG mode as nexthop based for ARS nexthop group selection.";
                    }
                  }
                  default "interface";
                  description "Specifies the ARS NHG mode for ARS nexthop group selection.";
            }

            leaf max_flows {
                type uint32;
                default 0;
                description  "Maximum number of flows that can be maintained per ARS profile.";
            }

            leaf sampling_interval {
                type uint32;
                default 16;
                description  "Sampling interval in microseconds for quality measure computation.";
            }

            leaf past_load_min_value {
                type uint16;
                default 0;
                description "Past load min value.";
            }

            leaf past_load_max_value {
                type uint16;
                default 0;
                description "Past load max value.";
            }

            leaf past_load_weight {
                type uint16;
                default 16;
                description "Past load weight.";
            }

            leaf future_load_min_value {
                type uint16;
                default 0;
                description "Future load min value.";
            }
            leaf future_load_max_value {
                type uint16;
                default 0;
                description "Future load max value.";
            }

            leaf future_load_weight {
                type uint16;
                default 16;
                description "Future load weight.";
            }

            leaf current_load_min_value {
                type uint16;
                default 0;
                description "Current load min value.";
            }

            leaf current_load_max_value {
                type uint16;
                default 0;
                description "Current load max value.";
            }

            leaf ipv4_enable {
                type boolean;
                default true;
                description "Whether ARS is enabled over IPv4 packets";
            }

            leaf ipv6_enable {
                type boolean;
                default true;
                description "Whether ARS is enabled over IPv6 packets";
            }
        }
        /* end of list ARS_PROFILE_LIST */
    }
    /* end of container ARS_PROFILE */
```

##### ARS_NEXTHOP_GROUP

```
    container ARS_NEXTHOP_GROUP {

        description "ARS-enabled Nexthop Groups";

        list ARS_NEXTHOP_GROUP_LIST {

            key "nhg_name";

            leaf nhg_name {
                type string;
                description "ARS nexthop group name";
            } 

            leaf assign_mode {
                type enumeration {
                    enum per_flowlet_quality{
                        description "Per flow-let assignment based on flow quality";
                    }
                    enum per_packet {
                        description "Per packet flow assignment based on port load";
                    }
                }
                default "per_flowlet_quality";
            }

            leaf flowlet_idle_time {
                type uint16 {
                    range 2..2047;
                }
                default 256;
                description  "Idle duration in microseconds. This duration is to classifying a flow-let in a macro flow.";
            }

            leaf max_flows {
                type uint32;
                default 512;
                description  "Maximum number of flow states that can be maintained per ARS object.";
            }

            leaf primary_path_threshold {
                type uint32;
                default 16;
                description  "Primary path metric";
            }

            leaf alternative_path_cost {
                type uint32;
                default 0;
                description  "Alternative path cost";
            }
        }
        /* end of list ARS_NEXTHOP_GROUP_LIST */
    }
    /* end of container ARS_NEXTHOP_GROUP */
```

##### ARS_NEXTHOP_MEMBERS

```
    container ARS_NEXTHOP_MEMBERS {

        description "ARS-enabled Nexthop Groups based on matching members";

        list ARS_NEXTHOP_MEMBER_LIST {

            key "vrf_name nexthop_ip";

            leaf vrf_name {
                type union {
                    type string {
                        pattern "default";
                    }
                    type leafref {
                        path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
                    }
                }
                description "VRF name";
            } 

            leaf nexthop_ip {
                type inet:ip-address;
                description "Nexthop-IP which is a member if nexthop group for which ARS behavior is desired";
            }

            leaf ars_nhg_name {
                description "ARS nexthop group name";
                mandatory true;
                type leafref {
                    path "/sars:sonic-ars/sars:ARS_NEXTHOP_GROUP/sars:ARS_NEXTHOP_GROUP_LIST/sars:nhg_name";
                }
            }
            leaf role {
                type enumeration {
                    enum primary_path{
                        description "Member is participating in primary path";
                    }
                    enum alternative_path {
                        description "Member is participating in alternative path";
                    }
                }
                default primary_path;
                description "NHG member's role";
            }
        }
        /* end of list ARS_NEXTHOP_MEMBER_LIST */
    }
    /* end of container ARS_NEXTHOP_MEMBERS */
```
##### ARS_INTERFACES

```
    container ARS_INTERFACES {

        list ARS_INTERFACE_LIST {
            description  "List of interfaces participating in ARS";
            key "if_name";

            leaf if_name {
                type leafref {
                    path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                }
                description "ARS-enabled interface name";
            }

            leaf scaling_factor {
                type uint32;
                default 10000;
                description "This factor used to normalize load measurements across ports with different speeds.";
            }

            leaf ars_nhg_name {
                description "ARS nexthop group name";
                mandatory true;
                type leafref {
                    path "/sars:sonic-ars/sars:ARS_NEXTHOP_GROUP/sars:ARS_NEXTHOP_GROUP_LIST/sars:nhg_name";
                }
            }

        }
        /* end of list ARS_INTERFACE_LIST */
    }
    /* end of container ARS_INTERFACES */
```

##### ARS_PORTCHANNEL_GROUP

```
    container ARS_PORTCHANNEL_GROUP {

        description "ARS-enabled portchannel groups";

        list ARS_PORTCHANNEL_GROUP_LIST {

            key "ars_portchanel_name";

            leaf ars_portchannel_name {
                type string;
                description "ARS portchannel group name";
            }
 
            leaf assign_mode {
                type enumeration {
                    enum per_flowlet_quality{
                        description "Per flow-let assignment based on flow quality";
                    }
                    enum per_packet {
                        description "Per packet flow assignment based on port load";
                    }
                }
                default "per_flowlet_quality";
            }

            leaf flowlet_idle_time {
                type uint16 {
                    range 2..2047;
                }
                default 256;
                description  "Idle duration in microseconds. This duration is to classifying a flow-let in a macro flow.";
            }

            leaf max_flows {
                type uint32;
                default 512;
                description  "Maximum number of flow states that can be maintained per ARS object.";
            }

            leaf primary_path_threshold {
                type uint32;
                default 16;
                description  "Primary path metric";
            }

            leaf alternative_path_cost {
                type uint32;
                default 0;
                description  "Alternative path cost";
            }

        }
        /* end of list ARS_PORTCHANNEL_LIST */
    }
    /* end of container ARS_PORTCHANNEL_GROUP */

```

##### ARS_PORTCHANNELS

```
    container ARS_PORTCHANNELS {

        list ARS_PORTCHANNEL_LIST {
            description  "List of portchannel participating in ARS";
            key "if_name";

            leaf if_name {
                type leafref {
                    path "/lag:sonic-portchannel/lag:PORTCHANNEL/lag:PORTCHANNEL_LIST/lag:name";
                }
                description "ARS-enabled portchannel name";
            }

            leaf ars_portchannel_name {
                description "ARS portchannel group name";
                mandatory true;
                type leafref {
                    path "/sars:sonic-ars/sars:ARS_PORTCHANNEL_GROUP/sars:ARS_PORTCHANNEL_GROUP_LIST/sars:portchannel_name";
                }
            }
            leaf-list alternative_path_members {
                type leafref {
                    path "/port:sonic-port/port:PORT/port:PORT_LIST/port:name";
                }
                description "Members of the LAG participating in alternative path";
            }
        }
        /* end of list ARS_PORTCHANNEL_LIST */
    }
    /* end of container ARS_PORTCHANNELS */
```

##### ACL_RULE

```
    container sonic-acl {

        container ACL_RULE {

            description "ACL_RULE part of config_db.json";

            list ACL_RULE_LIST {

                key "ACL_TABLE_NAME RULE_NAME";

                leaf ACL_TABLE_NAME {
                    type leafref {
                        path "/acl:sonic-acl/acl:ACL_TABLE/acl:ACL_TABLE_LIST/acl:ACL_TABLE_NAME";
                    }
                }

                leaf RULE_NAME {
                    type string {
                        length 1..255;
                    }
                } 
...
                leaf DISABLE_ARS_FORWARDING {
                    description "Disable ARS forwarding on matching packets";
                    type boolean;
                    default false;
                }
            }
         }
    }
```

#### Config DB Enhancements  

```
; New container ARS_PROFILE_TABLE
; ARS global configuration

key                     = ARS_PROFILE|profile_name

;field                  = value

algorithm               = "ewma"        ;Path quality calculation algorithm
ars_nhg_mode            = "interface"/  ;ARS NHG mode, to select the NHG for ARS enanbled NHG
                          "nexthop"     ; - 'interface' : ARS selection is based on interface list  
                                        ; - 'nexthop'   : ARS selection is based on nexthop list
                                        ;Default : "interface"
max_flows               = uint32        ;Maximum number of flows that can be maintained for ARS
sampling_interval       = uint32        ;Sampling interval in microseconds
past_load_min_value     = uint16        ;Minimum value of Past load range.
past_load_max_value     = uint16        ;Maximum value of Past load range.
past_load_weight        = uint16        ;Weight of the past load
future_load_min_value   = uint16        ;Minimum value of Future load range.
future_load_max_value   = uint16        ;Maximum value of Future load range.
future_load_weight      = uint16        ;Weight of the future load
current_load_min_value  = uint16        ;Minimum value of Current load range.
current_load_max_value  = uint16        ;Maximum value of Current load range.
ipv4_enable             = boolean       ;Whether ARS is enabled over IPv4 packets
ipv6_enable             = boolean       ;Whether ARS is enabled over IPv6 packets


Configuration example:

"ARS_PROFILE": {
    "ars_profile_default": {
        "algorithm": "ewma",
        "ars_nhg_mode": "interface",
        "max_flows" : "512",
        "sampling_interval": "10",
        "past_load_min_value" : "0",
        "past_load_max_value" : "100",
        "past_load_weight": "1",
        "future_load_min_value" : "0",
        "future_load_max_value" : "1000",
        "future_load_weight": "5",
        "ipv4_enable" : "true",
        "ipv6_enable" : "true"
    }
}
```

```
; New table ARS_NEXTHOP_GROUP_TABLE
; Nexhop groups enabled for ARS

key                       = ARS_NEXTHOP_GROUP|nhg_name                        ;Name which identifies ARS-nexhop-group 

;field                    = value

assign_mode               = "per_flowlet_quality" / "per_packet"              ;member selection assignment mode
flowlet_idle_time         = uint16                                            ;idle time for decting flowlet in macro flow. Relevant only for 
                                                                              ;assign_mode=pre_flowlet
max_flows                 = uint16                                            ;Max number of flows supported for ARS
primary_path_threshold    = uint16                                            ;Quality threshold for primary path 
alternative_path_cost     = uint16                                            ;cost of switching to alternative path

Configuration example:

"ARS_NEXTHOP_GROUP": {
    "ars_l3_group1" : {
        "assign_mode" : "per_flowlet_quality",
        "flowlet_idle_time" : "256",
        "max_flows" : "512",
        "primary_path_threshold" : "100",
        "alternative_path_cost": "250"
    }
}
```

```
; New table ARS_NEXTHOP_MEMBER_TABLE
; Nexthop IPs associated with ARS-enabled Nexthop group

key                      = ARS_NEXTHOP_MEMBER|vrf_name|nexthop_ip            ;Nextop IP identifing nexhop-group member 

;field                   = value

ars_nhg_name             = string                                            ;ARS nexthop group Name
*role                    = "primary_path"/"alternative_path"                 ;Whether this memeber is part of primary or alternative path

Configuration example:

"ARS_NEXTHOP_MEMBER": {
    "default|1.1.1.10" : {
        "ars_nhg_name": "ars_l3_group1"
    },
    "default|2.2.2.20" : {
        "ars_nhg_name": "ars_l3_group1",
        "role": "alternative_path"
    },
    "default|3.3.3.30" : {
        "ars_nhg_name": "ars_l3_group1"
    }
}
```
```
; New table ARS_INTERFACE_TABLE
; ARS interfaces configuration

key                      = ARS_INTERFACE|if_name          ;ifname is the name of the ARS-enabled interface

;field                   = value

scaling_factor           = uint32                          ;Port speed normalization
ars_nhg_name             = string                          ;ARS nexthop group Name
Configuration example:

"ARS_INTERFACE": {
    "Ethernet0" : {
        "scaling_factor"        : "100"
        "ars_nhg_name"          : "ars_l3_group1"
    },
    "Ethernet8" : {}
}
```

```
; New table ARS_PORTCHANNEL_GROUP_TABLE
; LAGs enabled for ARS

key                      = ARS_PORTCHANNEL_GROUP|ars_po_name           ;Name which identifies ARS-portchannel-group 

;field                   = value

assign_mode              = "per_flowlet_quality" / "per_packet"    ;port selection assignment mode
flowlet_idle_time        = uint16                                  ;idle time for decting flowlet in macro flow. Relevant only for assign_mode=pre_flowlet
max_flows                = uint16                                  ;Max number of flows supported for ARS
primary_path_threshold   = uint16                                  ;Quality threshold for primary path 
alternative_path_cost    = uint16                                  ;cost of switching to alternative path

Configuration example:

"ARS_PORTCHANNEL_GROUP": {
    "ars_l2_group1" : {
        "assign_mode" : "per_flowlet_quality",
        "flowlet_idle_time" : "256",
        "max_flows" : "512",
        "primary_path_threshold" : "100",
        "alternative_path_cost": "250",
    }
}
```

```
; New table ARS_PORTCHANNEL_TABLE
; ARS portchannel configuration

key                              = ARS_PORTCHANNEL|if_name         ;ifname is the name of the ARS-enabled portchannel

;field                           = value

ars_portchannel_name             = string                          ;ARS portchannel group Name
alternative_path_members         = string                          ;Members of the LAG participating in alternative path
Configuration example:

"ARS_PORTCHANNEL": {
    "PortChannel1" : {
        "ars_portchannel_name"  : "ars_l2_group1"
        "alternative_path_members": {"Ethernet0", "Ethernet10"}
    },
    "PortChannel1" : {}
}
```
```

; Existing table ACL_RULE_TABLE
; ACL action for disabling ARS


key                     = ACL_TABLE_TYPE|TYPE_NAME

;field                  = value

matches                 = match-list                    ; list of matches for this table.
                                                        ; matches are same as in ACL_RULE table.
actions                 = action-list                   ; list of actions for this table.
                                                        ; [ ... , "DISABLE_ARS_FORWARDING"]

Configuration example:

"ACL_TABLE_TYPE": {
    "CUSTOM_1_ARS": {
        "MATCHES": [
            "SRC_IP",
        ],
        "ACTIONS": [
            "DISABLE_ARS_FORWARDING"
        ],
    }
}
"ACL_TABLE": {
    "MY_ACL_1": {
        "policy_desc": "Disable ARS operation",
        "type": "CUSTOM_1_ARS",
        "ports": [
            "Ethernet2",
            "Ethernet4",
            "Ethernet7"
        ]
    }
},
```

```
; Existing table ACL_RULE_TABLE
; ACL action for disabling ARS


key                     = ACL_RULE|ACL_TABLE_NAME|RULE_NAME

;field                  = value

DISABLE_ARS_FORWARDING  = boolean                       ;ARS operation disabled on matching packets

Configuration example:

"ACL_RULE": {
    "MY_ACL_1|NO_ARS" : {
        "SRC_IP": "10.2.130.0/24",
        "DISABLE_ARS_FORWARDING" : "true"
    }
}
```

#### State DB Enhancements  

Following new tables will be added to State DB for ARS capability storing.
ARS_CAPABILITY_TABLE|{{ARS-SAI-feature-name}}|{{SAI-attribute-name}}:
    "get": "true"/"false",
    "create": "true"/"false",
    "set": "true"/"false"

Entry examples:

```
"SAI_OBJECT_TYPE_ARS_PROFILE|SAI_ARS_PROFILE_ATTR_ALGO":
"get": "true"
"create": "true"
"set": "false"

"SAI_OBJECT_TYPE_LAG|SAI_LAG_ATTR_ARS_OBJECT_ID":
"get": "false"
"create": "false"
"set": "false"
```

### Counters

Following counters defined in SAI and will be supported via FlexCounters in phase 2:

| Level            | Supported SAI counters  |
| ---------------- | ----------------------- |
| lag              | SAI_LAG_ATTR_ARS_PACKET_DROPS<br>SAI_LAG_ATTR_ARS_PORT_REASSIGNMENTS
| nexthop group    | SAI_NEXT_HOP_GROUP_ATTR_ARS_PACKET_DROPS<br>SAI_NEXT_HOP_GROUP_ATTR_ARS_NEXT_HOP_REASSIGNMENTS<br>SAI_NEXT_HOP_GROUP_ATTR_ARS_PORT_REASSIGNMENTS|

Flex counter group will be created for each level.

### CLI changes

1. ARS LAG counter polling:
```
    counterpoll ars_lag <enable | disable >
```

2. ARS LAG counter polling interval
```
    counterpoll ars_lag inteval < interval-val-ms >
```

3. ARS LAG counters show
```
    show ars_lag_counters [name]
```

4. ARS NHG counter polling:
```
    counterpoll ars_nexthop_group <enable | disable >
```

5. ARS NHG counter polling interval
```
    counterpoll ars_nexthop_group inteval < interval-val-ms >
```

6. ARS NHG counters show
```
    show ars_nexthop_group_counters [vrf <vrf-name>] [prefix <prefix>]
```

* Show examples
    * show ars_lag_counters PortChannel001
```
 Name             Drops    Port reassignments
---------------   -----    ------------------
 PortChannel1       10           100
```

    * show ars_nexthop_group_counters default 192.168.0.0/24
```
 Name                          Drops   Nexhop reassignments     Port reassignments
--------------------------     -----   ---------------------    -------------------
 ars_nexthop_group               10             50                      100
```

### Warmboot and Fastboot Design Impact

During warmboot or fastboot, both ARS and ACL rules configurations are restored from the CONFIG_DB.
Counter polling is delayed at system startup.

#### Restrictions/Limitations

Implementation will be done in two phases. 
1. Phase 1 will support: 
    - Primary path only
    - Quality parameters
    - ARS NHG support 
    - Support RouteOrch managed NHGs
2. Phase 2 will support:
    - Support NhgOrch managed NHGs
    - ARS LAG support
    - Alternative path
    - Statistics

#### Unit Test cases  

Tests separated into two groups - mandatory and optional (only if supported by vendor sai) parts.

- Mandatory:

1. ARS Profile Creation
    * Verify that ARS profiles are created successfully with valid parameters.
    * Test error handling for invalid profile configurations.

2. ARS Nexthop Group Creation
    * Verify that ARS nexthop group are created successfully with valid parameters.
    * Test error handling for invalid configuraitons.

3. ARS Nexthop Member Creation 
    * Verify that ARS nexthop member are created successfully with valid parameters.
    * Test error handling for invalid configurations.

4. Enabling/Disabling ARS on interface
    * Ensure ARS is enabled on specified interfaces.
    * Validate behavior when enabling ARS on unsupported interfaces.

5. ARS for Nexthop Groups (L3 traffic)
    * Confirm that ARS correctly applies to nexthop groups for Adaptive Routing.
    * Validate when ARS nhg mode is interface mode.
        * Validate per nexthop matching when port is enabled for ARS.
        * Validate per nexthop not-matching when port is disabled for ARS.
        * Validate NHG creation via routeorch.
           * Validate the ARS created for prefix to list of nexthop list.
        * Validate NHG creation via nhgorch (Phase 2).
            * Validate ARS enable on new/existing nexthop group.
            * Validate ARS enable on nexthop group member add/delete.
        * Check load balancing when overload single member.
        * Test failover scenario on link down.
        * Check load balancing when adding/removing Nexthop Group member.
        * Check load balancing when nexthop member is LAG.
        * Verify IPv4/IPv6 traffic.
        * Validate per flowlet/per packet distribution.
        * Validate when ars nhg mode is Nexthop.
    * Validate when ARS nhg mode is nexthop mode.
        *  Repeat all validation steps listed above.

6. Validation of counter for Nexthop Groups 
    * Enable counter for nexthop group.
    * Validate configuration of polling interval.
    * Validate drops, reassignment for nexthop/port counters.

7. ARS Portchannel Group Creation (Phase 2).
    * Verify that ARS portchannel group are created successfully with valid parameters.
    * Test error handling for invalid configuraitons.

8. ARS Portchannel Creation (Phase 2).
    * Verify that ARS group are created successfully with valid parameters.
    * Test error handling for invalid configuraitons.

9. ARS over LAGs (L2 traffic, Phase 2)
    * Validate ARS behavior over Link Aggregation Groups (LAGs) for Adaptive Switching.
    * Validate ARS enabled on portchannel group and add/remove members.
    * Check load balancing when overload single port.
    * Test failover scenario on link down.
    * Check load balancing when adding/removing port.
    * Validate per flowlet/per packet distribution.

10. Validation of counter for LAGs (Phase 2).
    * Enable counter for LAGs.
    * Validate configuration of polling interval.
    * Validate drop and port reassignments counters.

- Optional:

1. Path quality metrics
    * Verify future load affect on load-balancing
    * Verify current load affect on load-balancing

3. Alternative path (Phase 2)
    * Verify switching to alternative path for NHG
    * Verify switching to alternative path for LAG

#### System Test cases

1. Warm/Fast reboot
    * Verify that ARS configurations are preserved across reboots.
    * verify that ACL configurations are preserved across reboots.