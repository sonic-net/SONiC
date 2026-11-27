# FRR Protection Switching with ICMP hardware offload
FRR Protection Switching using ICMP hardware offload is a feature aimed at improving switchover time in Dual ToR architecture.

## Table of Contents

<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->

<!-- code_chunk_output -->

- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviation](#3-definitionsabbreviation)
- [4. Overview](#4-overview)
- [5. Requirements](#5-requirements)
  - [5.1 SONiC Requirements](#51-sonic-requirements)
  - [5.2 ASIC Requirements](#52-asic-requirements)
- [6. Hardware based Nexthop Protection Group Architecture](#6-hardware-based-nexthop-protection-group-architecture)
- [7. High-Level Design](#7-high-level-design)
  - [7.1 Orchagent](#71-orchagent)
    - [7.1.1 NhgOrch](#711-nhgorch)
    - [7.1.2 MuxOrch](#712-muxorch)
    - [7.1.3 MuxCableOrch](#713-muxcableorch)
    - [7.1.4 MuxNbrHandler](#714-muxnbrhandler)
      - [7.1.4.1 Neighbor Handling](#7141-neighbor-handling)
      - [7.1.4.2 ECMP Route Handling](#7142-ecmp-route-handling)
    - [7.1.5 IcmpOrch](#715-icmporch)
    - [7.1.6 Debounce Handling](#716-debounce-handling)
  - [7.2 LinkMgrd](#72-linkmgrd)
- [8. DB Schema Changes](#8-db-schema-changes)
  - [8.1 Config-DB](#81-config-db)
  - [8.2 App-DB](#82-app-db)
  - [8.3 State-DB](#83-state-db)
- [9. Command Line](#9-command-line)
  - [9.1 Show CLI](#91-show-cli)
- [10. Future Enhancements](#10-future-enhancements)
- [11. Limitations](#11-limitations)
- [12. Error Handling and Failure Scenarios](#12-error-handling-and-failure-scenarios)
- [13. Testing](#13-testing)
<!-- /code_chunk_output -->

## 1. Revision
| Rev |     Date    |         Author        |          Change Description      |
|:---:|:-----------:|:---------------------:|:--------------------------------:|
| 1.0 | 02/09/2026  | Manas Kumar Mandal    | Initial Version                  |

## 2. Scope
This document describes high level design details of SONiC's FRR hardware protection switching using ICMP hardware offloaded session for dual ToR architecture.

## 3. Definitions/Abbreviation
| Abbreviation | Definition |
|:------------:|:----------:|
| FRR          | Fast ReRoute |
| ToR          | Top of Rack |
| DualToR      | Dual Top of Rack |
| ICMP         | Internet Control Message Protocol |
| SAI          | Switch Abstraction Interface |
| NHG          | Next Hop Group |
| FDB          | Forwarding Database |
| IPinIP       | IP-in-IP Encapsulation |

## 4. Overview
SONiC uses ICMP echo request and reply packets to monitor the connectivity between server blades and the ToR switches in DualToR architecture. When an ICMP session state change is detected, SONiC switches traffic by reprogramming routes and neighbors. This reprogramming involves multiple SAI calls from SONiC, leading to unpredictable delays in switchover time. As a result, switchover performance cannot be guaranteed. FRR hardware protection switching addresses these limitations by handling switchover in hardware as specified by the SAI enhancement related to **SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION**.

## 5. Requirements
### 5.1 SONiC Requirements
  * Support of ICMP hardware offloaded sessions for dual ToR architecture is a prerequisite for this feature.
  * Support FRR hardware protection switching using ICMP hardware offloaded session for dual ToR architecture.
  * Support administrative failover switching by toggling members of nexthop protection group based on **admin_active**/**admin_standby** state values in MUX_CABLE_TBL.
  * Support prefix-route based neighbors for hardware based protection switching. Explicit neighbor-mode configuration is not needed for hardware based protection switching although orchagent will transition to use prefix-route based neighbors when hardware based protection switching is enabled.
  * Process cable config **failover_mode** knob to differentiate between software based failover switching and FRR hardware protection failover switching.
  * When **failover_mode** is not configured, the default value is **software**, preserving the existing software-based failover switching behavior. No behavioral change occurs for existing deployments that do not opt in.
  * Backward compatible with existing software based failover switching. When **failover_mode** is set to **hardware** but the ASIC does not support nexthop protection groups, SONiC will fall back to software based failover switching transparently.
  * Create nexthop protection group for FRR switchover based on the config.
  * Maintain mapping of mux cable and ICMP echo session object id.
  * The existing **state** field in App-DB MUX_CABLE_TBL is extended with two new values: **admin_active** and **admin_standby**. LinkMgrd will use these values for admin-initiated switching in both **software** and **hardware** modes. Existing **active**/**standby** values continue to be used for ICMP session-state-driven switching, preserving backward compatibility with older LinkMgrd versions.

### 5.2 ASIC Requirements
   * Support **SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION** type of next hop group.
   * Support **SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE** attribute as this allows SONiC to administratively toggle the protection group members in hardware overriding the automatic toggling of protection group members based on the ICMP session state.
   * Support **NO_HOST_ROUTE** SAI neighbor attribute. Hardware based switching mode uses prefix-route based neighbors, which require the platform to support this attribute. If the platform does not support **NO_HOST_ROUTE**, hardware based switching mode cannot be enabled.
   * Support bulk error notifications for nexthop protection groups to report hardware switchover failures back to SONiC (see [Section 12](#12-error-handling-and-failure-scenarios)).
   * Support protection NHG level switchover counters for observability (new SAI specification to be proposed -- see [Section 10](#10-future-enhancements)).

## 6. Hardware based Nexthop Protection Group Architecture
**SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION** type of next hop group enables fast switchover of traffic between primary and backup next hops in hardware. This is achieved by programming both primary and backup next hops in hardware and toggling of nexthops takes place in hardware without any extra programming from SONiC for switchover. This eliminates the need to reprogram all routes during switchover and enables fast failover switching.

Following diagram shows the high level SAI forwarding pipeline of hardware based nexthop protection group. The traffic is switched in hardware between primary and standby nexthop based on the state of the monitored ICMP hardware offloaded session of the mux port, without any involvement of SONiC for failover switching.
<div align="center"> <img src=image/nhprot_architecture.png height=350 width=1300 /> </div>

## 7. High-Level Design
Following diagram describes high level interaction of components in SONiC.
<div align="center"> <img src=image/nhprot_high_level_components.png width=1200 /> </div>


### 7.1 Orchagent
#### 7.1.1 NhgOrch
NhgOrch manages the lifecycle of nexthop protection groups in hardware. It extends the existing NhgOrch infrastructure to support **SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION** groups alongside the existing ECMP NHGs. The protection NHG implementation derives from the common NhgCommon base, which provides:

  * **Capacity accounting** -- protection NHG resource usage is tracked alongside ECMP NHGs, giving orchagent an accurate view of overall hardware NHG resource consumption.
  * **Consistent lifecycle management** -- creation, update, and removal of protection NHGs follow the same patterns as ECMP NHGs.

NhgOrch exposes APIs for the following protection NHG operations:
  * Creating a nexthop protection group with primary and backup nexthop members.
  * Updating nexthop protection group member attributes (e.g., setting **SAI_NEXT_HOP_GROUP_MEMBER_ATTR_MONITORED_OBJECT**).
  * Toggling **SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE** for administrative switchover.
  * Removing a nexthop protection group and its members.

**ProtNhgOrch** is a separate orch that registers for and processes bulk error notifications from SAI for protection NHGs. When the hardware fails to complete a switchover for one or more protection NHGs, SAI sends a bulk error notification identifying the failed NHG objects. ProtNhgOrch receives this notification, correlates the failed NHG OIDs with the corresponding mux ports, and forwards the failure information to MuxOrch. MuxOrch then handles the retry and failure marking logic (see [Section 12](#12-error-handling-and-failure-scenarios)).

MuxOrch is the primary consumer of NhgOrch APIs for dual-ToR. Other orchagent components can reuse the same interfaces in the future for additional features.

#### 7.1.2 MuxOrch
This feature introduces a new config knob **failover_mode** to differentiate between software based failover switching and FRR hardware protection failover switching that will use nexthop protection group to switch traffic. MuxOrch will perform a capability check for hardware protection group support by querying the SAI switch attributes. If the ASIC supports **SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION**, MuxOrch will create nexthop protection group for each mux neighbor and maintain a mapping of mux neighbors and nexthop protection groups based on this config knob. If the capability check fails, MuxOrch will fall back to software based failover switching.
MuxOrch creates the IPinIP tunnel based on the peer_switch configuration. Currently IPinIP tunnel destination next hop is created when mux state changes to standby. However, with **hardware** failover_mode it will create the IPinIP tunnel destination next hop in advance and add this as the backup member of the nexthop protection group.
MuxOrch will need to program the monitored ICMP offload session's object id as the **SAI_NEXT_HOP_GROUP_MEMBER_ATTR_MONITORED_OBJECT** in the nexthop protection group. For this MuxOrch will subscribe to notifications from IcmpOrch for ICMP session creation and will maintain a mapping of mux port and ICMP session object id. When MuxOrch receives notification for session creation from IcmpOrch, it will update the nexthop member attribute to program the monitored session object id.

Following diagram shows MuxOrch component level flow for admin_active/admin_standby and failover_mode handling.
<div align="center"> <img src=image/config_mux_mode_admin_role.png width=1200 /> </div>

#### 7.1.3 MuxCableOrch
MuxCableOrch in orchagent is the component responsible for consuming mux state from App DB MUX_CABLE_TABLE and performing failover switching. Currently this component updates all routes whenever a failover switchover is needed. When **failover_mode** is set to **hardware** in MuxOrch, MuxCableOrch will program the routes with the nexthop protection group OID as destination once during initial setup. Since the route destination is the protection NHG OID, subsequent ICMP session state changes (`active`/`standby`) are handled entirely in hardware -- MuxCableOrch does not need to reprogram routes or swap next hops during switchover. The only route programming from MuxCableOrch in **hardware** mode occurs during initial route creation and during admin-initiated manual switching (`admin_active`/`admin_standby`).

Following diagram shows component level flow for failover switching.
<div align="center"> <img src=image/link_stateup_switchover.png width=1200 /> </div>

#### 7.1.4 MuxNbrHandler
Currently when FDB changes or neighbor changes, neighbors are updated based on the state of mux. The neighbor handler also handles failover switching based on MUX state changes. With **hardware** failover mode, a new neighbor handler will be introduced to handle failover switching based on **admin_active**/**admin_standby** state values.

##### 7.1.4.1 Neighbor Handling

**Current behavior in prefix-route mode:**
In the existing prefix-route mode, failover switching is done by manipulating what each mux neighbor's prefix route (/32) points to:

  * **update (active/standby):** The neighbor handler sets the prefix route to the local neighbor next hop or tunnel next hop based on the state of mux.
  * **enable (active):** The neighbor handler sets the prefix route to the local neighbor next hop. The standalone tunnel route for this neighbor is removed.
  * **disable (standby):** The neighbor handler sets the prefix route to the tunnel next hop.

This means every failover switchover involves reprogramming prefix routes for each affected mux neighbor.

**New behavior with hardware protection switching:**
A new neighbor handler will be introduced for hardware protection switching. The new handler will not update the neighbor's prefix route on ICMP session state changes (`active`/`standby`) -- those are handled entirely in hardware by the nexthop protection group. The new handler will act only on admin-initiated state changes and neighbor updates:

  * **update (active/standby):** When a neighbor gets updated, the neighbor handler sets the prefix route to the hardware based protection nexthop group comprising of the local neighbor nexthop as its primary member and the tunnel next hop as its secondary member.
  * **admin_active:** The neighbor handler sets the protection NHG's **SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE** attribute to **SAI_NEXT_HOP_GROUP_ADMIN_ROLE_PRIMARY**.
  * **admin_standby:** The neighbor handler sets the protection NHG's **SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE** attribute to **SAI_NEXT_HOP_GROUP_ADMIN_ROLE_STANDBY**.

##### 7.1.4.2 ECMP Route Handling

**Current behavior in prefix-route mode:**
The tunnel next hop is never added as a member of ECMP next hop groups. Instead, failover switching manipulates which neighbor next hops are present in ECMP NHGs:

  * **enable (active):** Point the ECMP route to the active nexthop member of the ECMP NHG.

  * **disable (standby):** Point the ECMP route to the backup nexthop member of the ECMP NHG if it is the last active member in the NHG. If there are other active members in the NHG, point the ECMP route to the first active member in the NHG.

This means every failover switchover involves updating ECMP NHG membership and potentially scanning all ECMP routes for active mux neighbors. In the first release of this feature, orchagent will continue to program ECMP routes to point to the tunnel next hop for standby state for backward compatibility.

**Planned enhancement with hardware protection switching:**
In future releases, ECMP routes will point to the protection NHG. The protection NHG will have all the primary nexthops with their monitored object set to the corresponding ICMP session object id. When a member's ICMP session state changes to standby, hardware will update the member's observed role to **SAI_NEXT_HOP_GROUP_MEMBER_OBSERVED_ROLE_INACTIVE** and will not participate in forwarding traffic. If no active neighbors remain, the backup nexthop member's observed role will move to **SAI_NEXT_HOP_GROUP_MEMBER_OBSERVED_ROLE_ACTIVE** and will participate in forwarding traffic.

This will eliminate the ECMP NHG membership manipulation and the ECMP route scanning that currently occurs during switchover in prefix-route mode. See [Section 10.2](#102-ecmp-route-handling-with-protection-nhg) for SAI specification plans.

Following diagram shows ECMP route handling with hardware protection switching with multiple primary nexthops and one backup nexthop. The protection NHG will switch to secondary nexthop only when all the monitored sessions object ids are set to standby, until then the protection NHG will continue to forward traffic through the primary nexthops.
<div align="center"> <img src=image/ECMP_NextHop_ProtectionGroup.png width=1200 /> </div>

#### 7.1.5 IcmpOrch
IcmpOrch will notify MuxOrch on ICMP session creation and deletion. On session creation, MuxOrch uses the session object id to program **SAI_NEXT_HOP_GROUP_MEMBER_ATTR_MONITORED_OBJECT** on the nexthop protection group member. On session deletion, MuxOrch clears the monitored object attribute so that the protection group member does not reference a stale session.

#### 7.1.6 Debounce Handling
The nexthop protection group members use the ICMP hardware offloaded session -- not the physical port state -- as the monitored object. This provides built-in debounce for protection switchovers: a switchover fires only after multiple consecutive ICMP probe failures exceed the configured threshold, so transient link flaps or brief packet loss are absorbed without triggering a switchover. Using port state directly would cause immediate switchover and switchback on momentary link bounces, leading to unnecessary traffic disruption.

The effective debounce window equals roughly probe interval x retry count (e.g., 100ms x 3 = ~300ms). Operators can tune the ICMP session timers to balance switchover latency against flap suppression.

### 7.2 LinkMgrd
LinkMgrd is mostly agnostic to the use of nexthop protection groups; the only adaptation required is the use of extended state values for admin-initiated switching.

Currently LinkMgrd uses a common mux **state** field in MUX_CABLE_TBL with values `active`/`standby` for both manual config-based switching and ICMP session-state based switching. To differentiate between these two types of switching, two new state values are introduced: **admin_active** and **admin_standby**. LinkMgrd will write `admin_active`/`admin_standby` for admin-initiated (config-driven) switching and continue to write `active`/`standby` for ICMP session-state-driven switching. Orchagent distinguishes the trigger source by inspecting the state value itself. For existing neighbor modes, `admin_active` and `admin_standby` invoke the same active/standby routines, preserving backward compatibility.

## 8. DB Schema Changes

### 8.1 Config-DB
A new field failover_mode in **MUX_CABLE** config table to support this feature:
  * **failover_mode**
    * software : Failover switching with existing mechanism using software based failover switching. This is default value.
    * hardware : Failover switching using hardware based nexthop protection group.

```
MUX_CABLE|PORTNAME:
  failover_mode: software/hardware // New field to indicate hardware based protection switching for this mux port
```

### 8.2 App-DB
The existing **state** field in App DB **MUX_CABLE_TBL** is extended with two new values [admin_active|admin_standby] to differentiate admin-initiated switching from ICMP session-state-driven switching:

```
MUX_CABLE_TBL|PORTNAME:
  state: active/standby/admin_active/admin_standby
```

  * **active** / **standby** -- ICMP session-state-driven switching, written by LinkMgrd when ICMP session state changes. Older LinkMgrd versions continue to use only these values.
  * **admin_active** / **admin_standby** -- admin-initiated (config-driven) switching, written by LinkMgrd when the operator manually triggers a switchover. For older neighbor modes in orchagent, these invoke the same routines as `active`/`standby`, preserving backward compatibility.

### 8.3 State-DB
No new State-DB schema changes are introduced as part of this feature. The existing MUX_CABLE_TABLE in State-DB will continue to reflect the operational mux state as determined by the hardware protection switching.

## 9. Command Line

The **failover_mode** field is configured via `config_db.json` as part of the **MUX_CABLE** table. No separate config CLI is introduced for this field; it follows the existing pattern for mux cable configuration.

### 9.1 Show CLI

**Existing CLI to show mux config**
`show mux config` will be enhanced to show the new field failover_mode.

```
$ show mux config
SWITCH_NAME        PEER_TOR
-----------------  ----------
lab-switch-2  10.1.0.33
port        state    ipv4             ipv6               cable_type     soc_ipv4
----------  -------  ---------------  -----------------  -------------  ---------------
Ethernet4   auto     192.168.0.2/32   fc02:1000::2/128   active-active  192.168.0.3/32
Ethernet8   auto     192.168.0.4/32   fc02:1000::4/128   active-active  192.168.0.5/32
```

**New CLI to show mux config**
```
$ show mux config
SWITCH_NAME        PEER_TOR
-----------------  ----------
lab-switch-2  10.1.0.33
port        state    ipv4             ipv6               cable_type     soc_ipv4         failover_mode
----------  -------  ---------------  -----------------  -------------  ---------------  --------------
Ethernet4   auto     192.168.0.2/32   fc02:1000::2/128   active-active  192.168.0.3/32   hardware
Ethernet8   auto     192.168.0.4/32   fc02:1000::4/128   active-active  192.168.0.5/32   software
```

## 10. Future Enhancements

### 10.1 Protection NHG Switchover Counters
Per-port counters are not applicable for switchover observability because hardware protection switching monitors the ICMP offloaded session, not the physical port state. A new SAI specification will be proposed to define switchover counters scoped to the **SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION** object, tracking successful switchover events per NHG. Note that a session state notification from the hardware does not imply a successful switchover; the counter will be incremented only on confirmed switchovers.

A `show mux switchover status` CLI will present these counters in a per-NHG summary, and a platform CLI will be added to show switchover timestamps for each event.

### 10.2 ECMP Route Handling with Protection NHG
See [Section 7.1.4.2](#7142-ecmp-route-handling) for the planned enhancement to integrate ECMP routes with nexthop protection groups. A new SAI specification will be proposed to define the required attributes and behaviors.

## 11. Limitations
- Warm reboot and fast reboot with nexthop protection groups have not been validated and require additional testing before being supported.

## 12. Error Handling and Failure Scenarios
- **ICMP session creation failure:** If IcmpOrch fails to create the hardware offloaded ICMP session, MuxOrch will not receive the session object id notification. The nexthop protection group member will remain without a monitored object, and failover switching will fall back to software-based failover switching for the affected mux port.
- **ASIC does not support SAI_NEXT_HOP_GROUP_TYPE_HW_PROTECTION:** If the ASIC returns a failure when creating the nexthop protection group, MuxOrch will log an error and the mux port will continue to operate in software-based failover switching mode.
- **Monitored ICMP session deletion:** If the monitored ICMP session is deleted while the nexthop protection group is active, the nexthop protection group member's monitored object attribute will become stale. MuxOrch should handle session deletion notifications from IcmpOrch and update or remove the monitored object attribute accordingly.
- **Hardware protection switchover failure:** When a hardware-initiated switchover fails for one or more nexthop protection groups, SAI sends a bulk error notification identifying the failed NHGs. ProtNhgOrch processes this bulk notification and forwards the failure information to MuxOrch. MuxOrch then retries the switchover for the failed NHGs by setting **SAI_NEXT_HOP_GROUP_ATTR_ADMIN_ROLE** to force the transition via admin mode. If the admin-mode retry also fails, MuxOrch marks the switchover as failed and the neighbor state as inconsistent. This keeps the failure handling behavior consistent with software-based failover switching mode, where a failed switchover similarly results in an inconsistent neighbor state that requires operator intervention or a subsequent recovery event.

## 13. Testing
- Unit tests for LinkMgrd
- Gmock and VS based unit tests for NhgOrch / MuxOrch / MuxCableOrch / MuxNbrHandler / IcmpOrch
- Unit tests for Yang-model and CLIs
- Existing SONiC Management tests for dual-ToR should continue to pass without regression.
- New SONiC Management tests for dual-ToR:
    - Add support for hardware based ICMP echo session configurations
    - Add support for hardware based protection switching configurations
    - Verify switchover time meets the 50ms target requirement for hardware based protection switching
    - Verify admin_active/admin_standby based manual failover switching with nexthop protection group
