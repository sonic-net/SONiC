# BGP SRv6 Global Routing Table (GRT) HLD <!-- omit in toc -->

## Table of Contents <!-- omit in toc -->
- [1. Revision](#1-revision)
- [2. Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Overview](#4-overview)
	- [4.1. Example](#41-example)
		- [4.1.1. Reference Topology](#411-reference-topology)
		- [4.1.2. Control Plane](#412-control-plane)
		- [4.1.3. Data Plane](#413-data-plane)
- [5. Requirements](#5-requirements)
	- [5.1. Functional Requirements](#51-functional-requirements)
		- [5.1.1. Control plane](#511-control-plane)
		- [5.1.2. Data plane](#512-data-plane)
	- [5.2. Configuration and Management Requirements](#52-configuration-and-management-requirements)
- [6. Architecture Design](#6-architecture-design)
- [7. High-Level Design](#7-high-level-design)
	- [7.1. Egress router](#71-egress-router)
	- [7.2. Ingress router](#72-ingress-router)
- [8. Configuration and Management](#8-configuration-and-management)
	- [8.1. Configuration workflow](#81-configuration-workflow)
		- [8.1.1. Agent selection](#811-agent-selection)
		- [8.1.2. bgpcfgd path](#812-bgpcfgd-path)
		- [8.1.3. frrcfgd path](#813-frrcfgd-path)
	- [8.2. BGP SRv6 `CONFIG_DB` Schema](#82-bgp-srv6-config_db-schema)
		- [8.2.1. Configuration schema in ABNF format](#821-configuration-schema-in-abnf-format)
		- [8.2.2. Sample of `CONFIG_DB` snippet](#822-sample-of-config_db-snippet)
			- [8.2.2.1. Resulting FRR Configuration](#8221-resulting-frr-configuration)
	- [8.3. YANG model](#83-yang-model)
		- [8.3.1. `sonic-device_metadata`](#831-sonic-device_metadata)
		- [8.3.2. `sonic-srv6`](#832-sonic-srv6)
		- [8.3.3. `sonic-bgp-neighbor`](#833-sonic-bgp-neighbor)
	- [8.4. Operational verification](#84-operational-verification)
		- [8.4.1. Example](#841-example)
			- [8.4.1.1. Example 1: IPv6 BGP route table](#8411-example-1-ipv6-bgp-route-table)
			- [8.4.1.2. Example 2: Route details and Service SID](#8412-example-2-route-details-and-service-sid)
- [9. Testing Requirements/Design](#9-testing-requirementsdesign)
	- [9.1. Unit Test cases](#91-unit-test-cases)
	- [9.2. System Test cases](#92-system-test-cases)

## 1. Revision

| Rev  |   Date     |           Author                    | Change Description      |
| :--: | :--------: | :---------------------------------: | :---------------------: |
| 0.1  | 10/22/2026 | Carmine Scarpitta, Ahmed Abdelsalam | Initial version         |

## 2. Scope

This document describes the design for BGP SRv6 Global Routing Table (GRT) support in SONiC. 

BGP SRv6 GRT enables an egress router to advertise eligible IPv4 and IPv6 routes from its Global Routing Table (GRT) with SRv6 Service SIDs. The ingress router uses the advertised SID to encapsulate matching traffic for transport across the IPv6 underlay. 

FRR supports BGP SRv6 GRT with uDT46 SIDs starting with version 10.7.0. SONiC 202611 runs FRR 10.7.1 and therefore includes this capability. SONiC’s existing FRR-to-ASIC path also supports BGP SRv6 GRT: it distributes route and local SID state and programs the corresponding forwarding entries. This HLD addresses the remaining SONiC integration gaps. It adds BGP SRv6 GRT configuration fields to existing `CONFIG_DB` tables and corresponding leaves to existing YANG models, enabling operators to configure the feature, and extends `bgpcfgd` and `frrcfgd` to apply the settings to FRR.

## 3. Definitions/Abbreviations

| Definition/Abbreviation | Description |
| :--- | :--------- |
| API | Application Programming Interface
| APPL_DB | SONiC application database
| AS | Autonomous System
| ASIC | Application-Specific Integrated Circuit
| ASIC_DB | SONiC ASIC state database
| BGP | Border Gateway Protocol
| CE | Customer Edge
| CLI | Command-Line Interface
| CONFIG_DB | SONiC configuration database
| DA | Destination Address
| EGP | Exterior Gateway Protocol
| FPM | Forwarding Plane Manager
| FRR | FRRouting routing suite
| GRT | Global Routing Table
| HLD | High-Level Design
| IGP | Interior Gateway Protocol
| IPv4 | Internet Protocol version 4
| IPv6 | Internet Protocol version 6
| JSON | JavaScript Object Notation
| LocPrf | Local Preference
| MySID | Local SRv6 SID entry programmed on a router
| NH | Next Hop
| NLRI | Network Layer Reachability Information
| OID | Object Identifier
| P2P | Point-to-Point
| PE | Provider Edge
| RIB | Routing Information Base
| RPKI | Resource Public Key Infrastructure
| SA | Source Address
| SAI | Switch Abstraction Interface
| SDK | Software Development Kit
| SID | Segment Identifier
| SRv6 | Segment Routing over IPv6
| TLV | Type-Length-Value
| uDT46 | SRv6 endpoint behavior that decapsulates a packet and looks up its inner destination in an IPv4 or IPv6 table
| uSID | Micro-segment identifier
| VRF | Virtual Routing and Forwarding
| YANG | Data modeling language for network configuration and state

## 4. Overview

The Global Routing Table (GRT) holds a router’s global IPv4 and IPv6 routes. BGP SRv6 GRT uses BGP to advertise eligible routes from the egress router’s GRT to the ingress router, and SRv6 to carry traffic for those routes across the IPv6 underlay. The BGP SRv6 GRT procedures are specified in Sections 5.3 and 5.4 of [RFC 9252](https://www.rfc-editor.org/rfc/rfc9252.html).

An egress router advertises eligible GRT routes with a local SRv6 Service SID. The SID identifies the egress processing and can be reused across eligible IPv4 and IPv6 routes. The ingress router installs the received routes and uses the advertised SID to encapsulate matching packets in an outer IPv6 header. The underlay carries the packets to the egress router, which performs the Service SID’s behavior on the packet. For example, for a uDT46 SID, it removes the outer header, looks up the inner destination in its GRT, and forwards the packet.

### 4.1. Example

#### 4.1.1. Reference Topology

The reference topology is shown below:

<div align="center">
  <img src="images/bgp_srv6_grt_reference_topology.svg" alt="Reference Topology" width="80%">
</div>

PE1 and PE2 are connected through an IPv6 underlay. PE1’s loopback address is `fcbb:bbbb:1::1`, and its SRv6 locator prefix is `fcbb:bbbb:1::/48`. PE2’s loopback address is `fcbb:bbbb:2::1`, and its SRv6 locator prefix is `fcbb:bbbb:2::/48`.

The underlay must provide IPv6 reachability from each PE to the other PE’s loopback address and SRv6 locator prefix. Any technology may provide this reachability; underlay design is outside the scope of this HLD.

Once the loopbacks are reachable, PE1 and PE2 establish a BGP session using their IPv6 loopback addresses as peer endpoints. The session exchanges IPv4 and IPv6 GRT routes.

#### 4.1.2. Control Plane

<div align="center">
  <img src="images/bgp_srv6_grt_control_plane.svg" alt="SRv6 GRT Control Plane" width="80%">
</div>
 
In this example, P1 denotes the IPv6 GRT prefix `2001:db8:2:2::/64` behind CE2, and S1 denotes PE2’s local uDT46 Service SID `fcbb:bbbb:2:e000::`.

PE2 allocates local uDT46 Service SID S1 from its SRv6 locator and advertises GRT prefix P1 to PE1 in a BGP UPDATE. The UPDATE carries P1 in the route NLRI and PE2’s IPv6 loopback as the BGP next hop. It also includes a BGP Prefix-SID attribute containing an SRv6 L3 Service TLV. The TLV contains an SRv6 SID Information Sub-TLV, which carries S1 and specifies uDT46 as S1’s endpoint behavior. In this example, the SID Information Sub-TLV also includes a SID Structure Sub-Sub-TLV describing the format of the advertised SID. PE1 receives the UPDATE and learns route P1 with the advertised SID S1. It then installs a forwarding entry for P1 that encapsulates matching packets with S1 as the outer IPv6 destination.

#### 4.1.3. Data Plane

<div align="center">
  <img src="images/bgp_srv6_grt_data_plane.svg" alt="SRv6 GRT Data Plane" width="80%">
</div>
 
Once PE1 installs the forwarding entry for P1, it can forward traffic for P1 to PE2. Traffic is carried over SRv6. PE1 encapsulates packets whose destination matches P1 in an outer IPv6 packet with SID S1 as the destination address. The IPv6 underlay forwards each encapsulated packet toward PE2’s SRv6 locator prefix. At PE2, uDT46 removes the outer IPv6 header and looks up the inner destination in the GRT. PE2 then forwards the packet toward CE2.

## 5. Requirements

This section lists the functional, configuration, and management requirements for BGP SRv6 GRT.

### 5.1. Functional Requirements

#### 5.1.1. Control plane

* The egress router shall allocate a local Service SID from its configured SRv6 locator and advertise each eligible GRT route with that SID. The local Service SID is instantiated with the uDT46 behavior.
* The ingress router shall receive BGP UPDATEs carrying GRT routes and the advertised Service SID, install the selected routes, and program forwarding so matching packets are encapsulated with that SID as the outer IPv6 destination.

#### 5.1.2. Data plane

* The ingress router shall encapsulate packets matching an installed GRT route in an outer IPv6 packet whose destination is the Service SID advertised by the egress router, then forward them over the IPv6 underlay toward that router.
* The egress router shall receive packets addressed to its local Service SID and process them using the uDT46 Service SID’s behavior: remove the outer IPv6 header, look up the inner destination in the GRT, and forward the inner packet using the route selected by the lookup.

### 5.2. Configuration and Management Requirements

* The operator shall be able to configure the SRv6 locator from which the local Service SID is allocated.
* The operator shall be able to configure BGP to advertise IPv4 and IPv6 GRT routes with the local Service SID, optionally using a route-map to select which routes carry the SID.
* The operator shall be able to configure, for each BGP peer and address family (IPv4 unicast or IPv6 unicast), whether updates to that peer include the local Service SID.

## 6. Architecture Design

BGP SRv6 GRT builds on SONiC’s existing BGP and SRv6 architecture. Upstream FRR supports BGP SRv6 GRT with uDT46 Service SIDs starting with version 10.7.0. SONiC 202611 runs FRR 10.7.1, which supports BGP SRv6 GRT. This HLD adds BGP SRv6 GRT configuration fields to existing `CONFIG_DB` tables and corresponding leaves to existing YANG models, enabling operators to configure the feature in SONiC. It also extends `bgpcfgd` and `frrcfgd` to translate and apply those settings to FRR. This HLD does not modify FRR’s existing BGP SRv6 GRT implementation. The existing FRR-to-ASIC path for route and local SID distribution and forwarding programming also remains unchanged; no new architecture components or SAI APIs are introduced.

Figure below shows how the feature fits into SONiC’s existing architecture.

<div align="center">
  <img src="images/bgp_srv6_grt_architecture_design.svg" alt="Architecture Design" width="50%">
</div>

* SONiC stores switch configuration, including BGP configuration, in `CONFIG_DB`. A SONiC FRR configuration agent reads relevant entries from `CONFIG_DB` and translates them into FRR configuration.
* SONiC supports two agents for this purpose: `bgpcfgd` and `frrcfgd`. The agents use different configuration models: `bgpcfgd` follows the legacy template-based FRR configuration path, while `frrcfgd` responds to `CONFIG_DB` changes by issuing FRR CLI commands
* The `frr_mgmt_framework_config` field in the `DEVICE_METADATA|localhost` entry selects the active agent: `false` selects `bgpcfgd`, and `true` selects `frrcfgd`.
* Within FRR, `bgpd` manages BGP sessions and exchanges IPv4 and IPv6 GRT routes between PEs, while the SRv6 SID Manager allocates the egress PE’s local Service SID.
* `Zebra` sends route and local SID updates to `fpmsyncd` over FPM. `fpmsyncd` publishes these updates in `APPL_DB`’s `ROUTE_TABLE` and `SRV6_MY_SID_TABLE`, respectively.
* `RouteOrch` and `Srv6Orch` consume the corresponding `APPL_DB` tables and create objects in `ASIC_DB`.
* `syncd` programs the ASIC through SAI and the platform SDK.

## 7. High-Level Design

This section describes the configuration and egress and ingress processing for BGP SRv6 GRT.

### 7.1. Egress router

<div align="center">
  <img src="images/bgp_srv6_grt_high_level_design_egress.svg" alt="High-Level Design Egress" width="50%">
</div>
 
**Configuration.** The egress router is configured with an SRv6 locator from which its local uDT46 Service SID is allocated. The operator can configure, for each BGP peer and IPv4 or IPv6 unicast address family, whether advertised GRT routes include the local SID. An optional route map can further limit which GRT routes are advertised with the SID. The configuration schema, YANG model, and examples for BGP SRv6 GRT are described in Section [Configuration and Management](#8-configuration-and-management).

**SID allocation and local programming.** `bgpd` requests the SRv6 SID Manager to allocate a local uDT46 Service SID, S1, from the configured locator. After S1 is allocated, Zebra sends the local SID update to `fpmsyncd` over FPM. `fpmsyncd` publishes the SID in `APPL_DB`’s `SRV6_MY_SID_TABLE`. The table key encodes the SID structure lengths—block, node, function, and argument—and the SID:

```
Table: SRV6_MY_SID_TABLE
Key:   SRV6_MY_SID_TABLE:32:16:16:0:<S1>

Fields:
    action = udt46
    vrf    = "default"
```

Here, `action = udt46` specifies that packets addressed to S1 are decapsulated and their inner IPv4 or IPv6 destination is looked up. `vrf = default` selects the default/global VRF for that lookup. `Srv6Orch` consumes the entry and creates the corresponding MySID object in `ASIC_DB`. The object specifies uDT46 behavior and the default/global VRF; `syncd` then programs the ASIC through SAI.  The corresponding SAI MySID entry for S1 and its attributes are shown below.

<div align="center">
  <img src="images/bgp_srv6_grt_high_level_design_egress_sai.svg" alt="High-Level Design Egress SAI Programming" width="30%">
</div>
 
**Route advertisement.** `bgpd` advertises each eligible GRT route in a BGP UPDATE and includes the locally allocated SID S1 in the UPDATE for each eligible IPv4 or IPv6 route. The UPDATE carries the route prefix in the NLRI and includes a BGP Prefix-SID attribute. The BGP Prefix-SID attribute includes an SRv6 L3 Service TLV. Inside that TLV, an SRv6 SID Information Sub-TLV carries S1 and specifies uDT46 as the endpoint behavior. The SID Information Sub-TLV also carries a SID Structure Sub-Sub-TLV that describes S1’s format, including its block, node, function, and argument lengths.

<div align="center">
  <img src="images/bgp_srv6_grt_high_level_design_egress_advertisement.svg" alt="High-Level Design Egress Route Advertisement" width="80%">
</div>
 
### 7.2. Ingress router

<div align="center">
  <img src="images/bgp_srv6_grt_high_level_design_ingress.svg" alt="High-Level Design Ingress" width="50%">
</div>

**Configuration.** The operator configures the ingress router to establish a BGP session with the egress router and enables the IPv4 and/or IPv6 unicast address family to receive GRT routes from it. Section [Configuration and Management](#8-configuration-and-management) describes the related BGP peer and address-family configuration, `CONFIG_DB` schema, YANG model, and examples.

**Route reception.** Upon receiving a BGP UPDATE from the egress router, the ingress router learns route prefix P1 and Service SID S1. After BGP selects the best path for P1, `Zebra` sends the selected route and its associated SID to `fpmsyncd` over FPM. `fpmsyncd` publishes P1 in `APPL_DB`’s `ROUTE_TABLE`, with S1 in the `vpn_sid` field. For example:

```
Key: ROUTE_TABLE:<P1>

Fields:
    protocol = bgp
    nexthop = <egress PE’s BGP next hop>
    vpn_sid = <S1>
    ...
```

**Forwarding programming.** The corresponding route and SRv6 objects are created in `ASIC_DB`, and syncd then programs them on the ASIC through SAI. As a result, packets matching P1 are encapsulated with S1 as the outer IPv6 destination. The diagram below shows the corresponding SAI objects and the tunnel-map association.

<div align="center">
  <img src="images/bgp_srv6_grt_high_level_design_ingress_sai.svg" alt="High-Level Design Ingress SAI Programming" width="80%">
</div>


## 8. Configuration and Management

This section describes how BGP SRv6 GRT is configured in SONiC and how the operator can verify its operational status. BGP SRv6 GRT configuration is stored in `CONFIG_DB`. A SONiC FRR configuration agent reads the relevant entries and applies them to FRR. SONiC supports two agents for this purpose: `bgpcfgd` and `frrcfgd`. The `frr_mgmt_framework_config` field in `DEVICE_METADATA|localhost` selects the active agent. Figure below shows this configuration flow.

<div align="center">
  <img src="images/bgp_srv6_grt_configuration.svg" alt="BGP SRv6 GRT Configuration" width="50%">
</div>

### 8.1. Configuration workflow

#### 8.1.1. Agent selection

The `frr_mgmt_framework_config` field in `DEVICE_METADATA|localhost` selects the agent that manages FRR configuration. A value of `false` selects `bgpcfgd`; `true` selects `frrcfgd`. The agents are alternatives, and the selected agent applies the BGP SRv6 GRT configuration. The choice of agent does not change the `CONFIG_DB` schema.

#### 8.1.2. bgpcfgd path

When `bgpcfgd` is selected, it monitors the relevant BGP and SRv6 entries in `CONFIG_DB`. For each configuration change, it uses templates to generate the corresponding FRR configuration commands and applies them through `vtysh`. This design extends the relevant `bgpcfgd` handling and templates to support the BGP SRv6 GRT fields.

#### 8.1.3. frrcfgd path

When `frrcfgd` is selected, it subscribes to changes in the relevant `CONFIG_DB` entries. Its event handlers translate those changes into FRR CLI commands and apply them through `vtysh`. This design extends the handlers and command mappings to support the BGP SRv6 GRT configuration.

### 8.2. BGP SRv6 `CONFIG_DB` Schema

This section defines the `CONFIG_DB` entries for BGP SRv6 GRT. The schema is shared by `bgpcfgd` and `frrcfgd`.

#### 8.2.1. Configuration schema in ABNF format

The following ABNF describes the tables and fields used to configure the SRv6 locator, BGP neighbor settings, and SID advertisement policy:

```
; DEVICE_METADATA table
key                                = DEVICE_METADATA|localhost ; Device metadata configuration table
; field                            = value
bgp_srv6_locator                   = SRV6_MY_LOCATORS.key    ; SRv6 Locator used for Service SID allocation
bgp_srv6_ipv4_sid_advertise        = “true”/”false”          ; Enables or disables IPv4 GRT SID advertisement
bgp_srv6_ipv4_sid_prefix_list      = PREFIX_LIST.prefix_type ; Optional prefix list used to select IPv4           
                                                               routes for SID export
bgp_srv6_ipv6_sid_advertise        = “true”/”false”          ; Enables or disables IPv6 GRT SID advertisement
bgp_srv6_ipv6_sid_prefix_list      = PREFIX_LIST.prefix_type ; Optional prefix list used to select Ipv6           
                                                               routes for SID export
```

```
; BGP_NEIGHBOR table
key                = BGP_NEIGHBOR|vrf_name|neighbor ; BGP neighbor table
; field            = value
encapsulation_type = "srv6"/"srv6-relax"       ; Encapsulation mode for this neighbor
```

```
; SRV6_MY_LOCATORS table
key                = SRV6_MY_LOCATORS|locator_name
; field            = value
prefix             = locator_prefix      ; IPv6 address that represents the locator, 
                                           which is also the IPv6 prefix for all SIDs under the locator
format             = "usid-f3216"        ; the format of the SIDs allocated from this locator
```

#### 8.2.2. Sample of `CONFIG_DB` snippet

The following snippet shows an example BGP SRv6 GRT configuration in `CONFIG_DB`:

```json
{
  "DEVICE_METADATA": {
    "localhost": {
      "bgp_asn": "65001",
      "bgp_router_id": "10.125.1.1",
      "bgp_srv6_locator": "MAIN",
      "bgp_srv6_ipv4_sid_advertise": "true",
      "bgp_srv6_ipv4_sid_prefix_list": "BGP_SRV6_EXPORT_IPV4",
      "bgp_srv6_ipv6_sid_advertise": "true"
    }
  },
  "SRV6_MY_LOCATORS": {
    "MAIN": {
      "prefix": "fcbb:bbbb:1::",
      "format": "usid-f3216"
    }
  },
  "PREFIX_LIST": {
    "BGP_SRV6_EXPORT_IPV4|172.16.0.0/24": {
      "action": "deny",
      "seq": "1"
    },
    "BGP_SRV6_EXPORT_IPV4|0.0.0.0/0": {
      "action": "permit",
      "seq": "255",
      "le": "32"
    }
  },
  "BGP_NEIGHBOR": {
    "fcbb:bbbb:2::1": {
      "asn": "65102",
      "local_addr": "fcbb:bbbb:1::1",
      "name": "R2",
      "encapsulation_type": "srv6"
    },
    "fcbb:bbbb:3::1": {
      "asn": "65103",
      "local_addr": "fcbb:bbbb:1::1",
      "name": "R3",
      "encapsulation_type": "srv6-relax"
    }
  }
```

##### 8.2.2.1. Resulting FRR Configuration

The following excerpt shows the effective FRR configuration corresponding to the `CONFIG_DB` example above. The active configuration agent applies the settings to FRR: `bgpcfgd` uses its template-based path, while `frrcfgd` applies equivalent FRR CLI commands. Both paths result in the same BGP SRv6 GRT configuration.

```
segment-routing
 srv6
  locators
   locator MAIN
    prefix fcbb:bbbb:1::/48
    format usid-f3216
   !
  !
!

! IPv4 prefix filter and route-map used by BGP SID export
ip prefix-list BGP_SRV6_EXPORT_IPV4 seq 1 deny 172.16.0.0/24
ip prefix-list BGP_SRV6_EXPORT_IPV4 seq 255 permit 0.0.0.0/0 le 32

route-map RM_BGP_SRV6_EXPORT_IPV4 permit 10
 match ip address prefix-list BGP_SRV6_EXPORT_IPV4
!

router bgp 65001
 bgp router-id 10.125.1.1
 !
 neighbor fcbb:bbbb:2::1 remote-as 65102
 neighbor fcbb:bbbb:2::1 update-source fcbb:bbbb:1::1
 neighbor fcbb:bbbb:3::1 remote-as 65103
 neighbor fcbb:bbbb:3::1 update-source fcbb:bbbb:1::1
 !
 segment-routing srv6
  locator MAIN
 !
 address-family ipv4 unicast
  sid export auto behavior dt46 route-map RM_BGP_SRV6_EXPORT_IPV4
  neighbor fcbb:bbbb:2::1 activate
  neighbor fcbb:bbbb:2::1 encapsulation-srv6
  neighbor fcbb:bbbb:3::1 activate
  neighbor fcbb:bbbb:3::1 encapsulation-srv6-relax
 exit-address-family
 !
 address-family ipv6 unicast
  sid export auto behavior dt46
  neighbor fcbb:bbbb:2::1 activate
  neighbor fcbb:bbbb:2::1 encapsulation-srv6
  neighbor fcbb:bbbb:3::1 activate
  neighbor fcbb:bbbb:3::1 encapsulation-srv6-relax
 exit-address-family
!
```

### 8.3. YANG model

The YANG models define the types, constraints, and references for the `CONFIG_DB` fields described in Section [BGP SRv6 CONFIG_DB Schema](#82-bgp-srv6-config_db-schema). They apply to either FRR configuration agent.

#### 8.3.1. `sonic-device_metadata`

```yang
module: sonic-device_metadata
  +--rw sonic-device_metadata
     +--rw DEVICE_METADATA
        +--rw localhost
           +--rw bgp_asn?             inet:as-number
           +--rw bgp_router_id?       inet:ipv4-address
           +--rw bgp_srv6_locator?    -> /sonic-srv6/SRV6_MY_LOCATORS/SRV6_MY_LOCATORS_LIST/locator_name
           +--rw bgp_srv6_ipv4_sid_advertise?    boolean
           +--rw bgp_srv6_ipv4_sid_prefix_list?  -> /sonic-bgp-prefix-list/PREFIX_LIST/PREFIX_LIST_LIST/prefix_type
           +--rw bgp_srv6_ipv6_sid_advertise?    boolean
           +--rw bgp_srv6_ipv6_sid_prefix_list?  -> /sonic-bgp-prefix-list/PREFIX_LIST/PREFIX_LIST_LIST/prefix_type
```

| Field Name | Data Type | Supported Values / Constraints | Description
| :-- | :---------- | :---------- | :---------- |
| `bgp_srv6_locator` | `leafref` | Must reference an existing `locator_name` in `SRV6_MY_LOCATORS` | Selects the local SRv6 locator used by BGP SRv6 GRT.
| `bgp_srv6_ipv4_sid_advertise` | `boolean` | `true` or `false`; default `false` | Enables or disables Service SID advertisement for eligible IPv4 GRT routes.
| `bgp_srv6_ipv4_sid_prefix_list` | `leafref` | Optional; must reference an existing `prefix_type` in `PREFIX_LIST` containing IPv4 entries | Selects IPv4 GRT routes for SID advertisement. If omitted while SID advertisement is enabled, no prefix-list filter is applied.
| `bgp_srv6_ipv6_sid_advertise` | `boolean`  | `true` or `false`; default `false` | Enables or disables Service SID advertisement for eligible IPv6 GRT routes.
| `bgp_srv6_ipv6_sid_prefix_list` | `leafref` | 	Optional; must reference an existing `prefix_type` in `PREFIX_LIST` containing IPv6 entries | Selects IPv6 GRT routes for SID advertisement. If omitted while SID advertisement is enabled, no prefix-list filter is applied.

#### 8.3.2. `sonic-srv6`

```yang
module: sonic-srv6
  +--rw sonic-srv6
     +--rw SRV6_MY_LOCATORS
        +--rw SRV6_MY_LOCATORS_LIST* [locator_name]
           +--rw locator_name    string
           +--rw prefix          inet:ipv6-address
           +--rw format?         enumeration
```

| Field Name | Data Type | Supported Values / Constraints | Description
| :-- | :---------- | :---------- | :---------- |
| `locator_name` | `string` | Required list key; unique within the table | Name of the local SRv6 locator.
| `prefix` | `inet:ipv6-address` | Valid IPv6 address | Address representing the locator prefix.
| `format` | `enumeration` | `usid-f3216` | uSID format with a 32-bit block and 16-bit node ID.

#### 8.3.3. `sonic-bgp-neighbor`

```yang
module: sonic-bgp-neighbor
  +--rw sonic-bgp-neighbor
     +--rw BGP_NEIGHBOR
        +--rw BGP_NEIGHBOR_TEMPLATE_LIST* [neighbor]
           +--rw neighbor               union
           +--rw asn?                   uint32
           +--rw local_addr?            inet:ip-address
           +--rw name?                  string
           +--rw encapsulation_type?    enumeration
```

Field Name | Data Type | Supported Values / Constraints	Description
| :-- | :---------- | :---------- |
| `encapsulation_type` | `enumeration` | `srv6`, `srv6-relax` | SRv6 encapsulation setting for the BGP neighbor. `srv6` advertises only routes with an SRv6 SID; `srv6-relax` allows routes with or without a SID over the same BGP session.


### 8.4. Operational verification

Operators can inspect IPv4 and IPv6 GRT routes, including the SRv6 SID information received with them, using the existing BGP show commands.

| CLI | Description
| :-- | :---------- |
| `show ip bgp network [ipv4-prefix]` | Show IPv4 routes
| `show ipv6 bgp network [ipv6-prefix]` | Show IPv6 routes

#### 8.4.1. Example

##### 8.4.1.1. Example 1: IPv6 BGP route table

```text
> show ipv6 bgp network

BGP table version is 4, local router ID is 1.1.1.1, vrf id 0
Default local pref 100, local AS 65101
Status codes:  s suppressed, d damped, h history, u unsorted, * valid, > best, = multipath,
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self
Origin codes:  i - IGP, e - EGP, ? - incomplete
RPKI validation codes: V valid, I invalid, N Not found

     Network          Next Hop            Metric LocPrf Weight Path
 *>  2001:db8:2:2::/64 fcbb:bbbb:2::1          0         32768 ?

Displayed 1 routes and 1 total paths
```

##### 8.4.1.2. Example 2: Route details and Service SID

```text
> show ipv6 bgp network 2001:db8:2:2::/64

BGP routing table entry for 2001:db8:2:2::/64
Paths: (1 available, best #1, table default)
  Advertised to non peer-group peers:
  fcbb:bbbb:2::1
  65102
    fcbb:bbbb:2::1 from fcbb:bbbb:2::1 (2.2.2.2)
      Origin IGP, localpref 100, valid, internal, multipath, best (Router ID)
      Remote SID: fcbb:bbbb:2:e000::, uDT46, sid structure=[32 16 16 0 0 0]
      Last update: Thu Apr 22 02:13:30 2021
```

## 9. Testing Requirements/Design  

This section describes the unit and system tests used to verify the BGP SRv6 GRT design and its integration with SONiC.

### 9.1. Unit Test cases  

| Test case	| Description | Expected result
| :-------- | :---------- | :-------------- |
| `CONFIG_DB`/YANG validation: valid BGP SRv6 GRT configuration | Test a valid BGP SRv6 GRT configuration. | The configuration passes `CONFIG_DB`/YANG validation.
| `CONFIG_DB`/YANG validation: invalid BGP SRv6 GRT configuration | Test BGP SRv6 GRT configurations containing unsupported values, such as an unsupported locator format, or references to undefined route maps. | `CONFIG_DB`/YANG validation rejects the invalid configuration.
| `bgpcfgd` configuration handling | Add valid BGP SRv6 GRT configuration to `CONFIG_DB` and verify that `bgpcfgd` generates the corresponding FRR configuration. | The generated FRR configuration reflects the `CONFIG_DB` settings.
| `frrcfgd` configuration handling | Add valid BGP SRv6 GRT configuration to `CONFIG_DB` and verify that `frrcfgd` generates the corresponding FRR configuration. | The generated FRR configuration reflects the `CONFIG_DB` settings.

### 9.2. System Test cases

The system tests use the reference topology, in which PE1 and PE2 are connected through an IPv6 underlay. The underlay provides reachability to each PE’s loopback address and SRv6 locator prefix and carries SRv6 traffic between the PEs. PE1 and PE2 establish the service BGP session using their loopback addresses.

| Test case	| Description | Expected result
| :-------- | :---------- | :-------------- |
| IPv4 GRT route advertisement | Advertise an IPv4 GRT route with its Service SID and verify it at the ingress router. | The ingress router learns the route with its Service SID and installs forwarding for it.
| IPv6 GRT route advertisement | Advertise an IPv6 GRT route with its Service SID and verify it at the ingress router. | The ingress router learns the route with its Service SID and installs forwarding for it.
| SID export policy	| Configure a route-map for SID export and advertise routes that match and do not match the policy. | SONiC applies the configuration to FRR, and SID export follows the configured policy.
| IPv4 data-plane forwarding | Send traffic matching the IPv4 route through the SRv6 path to the egress router.	| The packet is encapsulated toward the Service SID, decapsulated at egress, and its inner destination is looked up in the IPv4 GRT.
| IPv6 data-plane forwarding | Send traffic matching the IPv6 route through the SRv6 path to the egress router.	| The packet is encapsulated toward the Service SID, decapsulated at egress, and its inner destination is looked up in the IPv6 GRT.

