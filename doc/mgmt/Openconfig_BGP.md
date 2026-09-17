# OpenConfig Model Support for SONiC BGP Feature

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Related Documents](#related-documents)
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
      * [3.1.1 SONiC Feature YANG and CONFIG_DB](#311-sonic-feature-yang-and-config_db)
      * [3.1.2 OpenConfig Modules](#312-openconfig-modules)
      * [3.1.3 UMF Translation (REST/gNMI to CONFIG_DB)](#313-umf-translation-restgnmi-to-config_db)
      * [3.1.4 FRR Programming (frrcfgd and Templates)](#314-frr-programming-frrcfgd-and-templates)
      * [3.1.5 OpenConfig Extensions](#315-openconfig-extensions)
      * [3.1.6 Mapping Table and Unit Tests](#316-mapping-table-and-unit-tests)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)
      * [3.2.2 APP DB](#322-app-db)
      * [3.2.3 STATE DB](#323-state-db)
      * [3.2.4 ASIC DB](#324-asic-db)
      * [3.2.5 COUNTER DB](#325-counter-db)
  * [4 OpenConfig to SONiC Mapping Table](#4-openconfig-to-sonic-mapping-table)
    * [4.1 BGP Global](#41-bgp-global)
    * [4.2 BGP Global AFI-SAFIs](#42-bgp-global-afi-safis)
    * [4.3 BGP Dynamic Neighbor Prefixes](#43-bgp-dynamic-neighbor-prefixes)
    * [4.4 BGP Neighbors](#44-bgp-neighbors)
    * [4.5 BGP Peer Groups](#45-bgp-peer-groups)
    * [4.6 Local Aggregates](#46-local-aggregates)
    * [4.7 Table Connections and Tables](#47-table-connections-and-tables)
  * [5 User Interface](#5-user-interface)
    * [5.1 Data Models](#51-data-models)
    * [5.2 REST API Support](#52-rest-api-support)
      * [5.2.1 GET](#521-get)
      * [5.2.2 PATCH](#522-patch)
      * [5.2.3 DELETE](#523-delete)
    * [5.3 gNMI Support](#53-gnmi-support)
      * [5.3.1 GET](#531-get)
      * [5.3.2 SET](#532-set)
      * [5.3.3 DELETE](#533-delete)
      * [5.3.4 SUBSCRIBE](#534-subscribe)
  * [6 Error Handling](#6-error-handling)
  * [7 Unit Test Cases](#7-unit-test-cases)
    * [7.1 Functional Test Cases](#71-functional-test-cases)
    * [7.2 Negative Test Cases](#72-negative-test-cases)


# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

[Table 2: Translation Flow Layers](#table-2-translation-flow-layers)

OpenConfig to SONiC mapping tables: [Section 4](#4-openconfig-to-sonic-mapping-table)


# Revision
| Rev | Date | Author | Change Description |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 12/02/2025 | Venkata Krishna Rao G, Anukul Verma | Initial version |

# About this Manual
This document provides general information about the OpenConfig configuration and management of BGP and local aggregates in SONiC corresponding to the openconfig-network-instance.yang and openconfig-bgp.yang modules. It describes how OpenConfig models are translated to SONiC CONFIG_DB entries and FRR bgpd/mgmtd configuration, and how operational state is returned over REST and gNMI.

BGP is configured under:
/network-instances/network-instance/protocols/protocol[identifier=BGP][name=bgp]/bgp

Local aggregates are configured under:
/network-instances/network-instance/protocols/protocol[identifier=LOCAL_AGGREGATE][name=bgp]/local-aggregates

# Related Documents
| Document | Description |
|----------|-------------|
| Management Framework.md | UMF architecture (REST, gNMI, translib, transformers) |
| Openconfig_Network_Instance.md | Core network-instance (VRF, interfaces, VLANs, FDB, protocol container overview) |
| OpenConfig_StaticRoute.md | Static routes |

# Scope
- This document describes the high level design of OpenConfig **BGP** and **local aggregate** configuration and operational retrieval in SONiC.
- **In scope:** REST and gNMI — Get, Set (POST/PUT/PATCH), Delete, and Subscribe on supported BGP YANG paths.
- **Out of scope:** SONiC KLISH CLI; `/network-instances/network-instance/evpn/`; `/network-instances/network-instance/connection-points/`; `bgp/fib-install-policy` (intentionally omitted); `bgp/neighbors/neighbor/graceful-restart` (`not-supported` in deviation); `l2vpn-evpn` under neighbor/peer-group `afi-safis/afi-safi` (`not-supported` in deviation).
- OpenConfig xpath roots:
  `/network-instances/network-instance/protocols/protocol[identifier=BGP][name=bgp]/bgp`
  `/network-instances/network-instance/protocols/protocol[identifier=LOCAL_AGGREGATE][name=bgp]/local-aggregates`
  `/network-instances/network-instance/table-connections`
  `/network-instances/network-instance/tables`
- Supported attributes in OpenConfig YANG tree (reflecting current UMF implementation):

```
module: openconfig-network-instance (+ openconfig-network-instance-ext, openconfig-bgp)
+--rw network-instances
   +--rw network-instance* [name]
      +--rw table-connections
      |  +--rw table-connection* [src-protocol dst-protocol address-family]
      |     +--rw src-protocol      -> ../config/src-protocol
      |     +--rw dst-protocol      -> ../config/dst-protocol
      |     +--rw address-family    -> ../config/address-family
      |     +--rw config
      |     |  +--rw src-protocol?     -> ../../../../tables/table/config/protocol
      |     |  +--rw address-family?   -> ../../../../tables/table[protocol=current()/../src-protocol]/config/address-family
      |     |  +--rw dst-protocol?     -> ../../../../tables/table/config/protocol
      |     |  +--rw import-policy*    -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
      |     |  +--rw oc-network-instance-ext:metric?   uint32
      |     +--ro state
      |        +--ro src-protocol?     -> ../../../../tables/table/config/protocol
      |        +--ro address-family?   -> ../../../../tables/table[protocol=current()/../src-protocol]/config/address-family
      |        +--ro dst-protocol?     -> ../../../../tables/table/config/protocol
      |        +--ro import-policy*    -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
      |        +--ro oc-network-instance-ext:metric?   uint32
      +--rw tables
      |  +--rw table* [protocol address-family]
      |     +--rw protocol          -> ../config/protocol
      |     +--rw address-family    -> ../config/address-family
      |     +--rw config
      |     |  +--rw protocol?         -> ../../../../protocols/protocol/config/identifier
      |     |  +--rw address-family?   identityref
      |     +--ro state
      |        +--ro protocol?         -> ../../../../protocols/protocol/config/identifier
      |        +--ro address-family?   identityref
      +--rw protocols
         +--rw protocol* [identifier name]
            +--rw identifier          -> ../config/identifier
            +--rw name                -> ../config/name
            +--rw config
            |  +--rw identifier?   identityref
            |  +--rw name?         string
            |  +--rw enabled?      boolean
            +--ro state
            |  +--ro identifier?   identityref
            |  +--ro name?         string
            |  +--ro enabled?      boolean
            +--rw local-aggregates
            |  +--rw aggregate* [prefix]
            |     +--rw prefix    -> ../config/prefix
            |     +--rw config
            |     |  +--rw prefix?            inet:ip-prefix
            |     |  +--rw oc-network-instance-ext:summary-only?      boolean
            |     |  +--rw oc-network-instance-ext:as-set?            boolean
            |     |  +--rw oc-network-instance-ext:export-policy?     -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
            |     +--ro state
            |        +--ro prefix?            inet:ip-prefix
            |        +--ro oc-network-instance-ext:summary-only?      boolean
            |        +--ro oc-network-instance-ext:as-set?            boolean
            |        +--ro oc-network-instance-ext:export-policy?     -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
            +--rw bgp
               +--rw global
               |  +--rw config
               |  |  +--rw as                                                            oc-inet:as-number
               |  |  +--rw router-id?                                                    oc-yang:dotted-quad
               |  |  +--rw oc-network-instance-ext:enable-default-ipv4-unicast-afi?                              boolean
               |  |  +--rw oc-network-instance-ext:max-dynamic-neighbor-prefixes?                                uint16
               |  |  +--rw oc-network-instance-ext:disable-ebgp-connected-route-check?                           boolean
               |  |  +--rw oc-network-instance-ext:fast-external-failover?                                       boolean
               |  |  +--rw oc-network-instance-ext:default-local-preference?                                     uint32
               |  +--ro state
               |  |  +--ro as                                                            oc-inet:as-number
               |  |  +--ro router-id?                                                    oc-yang:dotted-quad
               |  |  +--ro oc-network-instance-ext:enable-default-ipv4-unicast-afi?                              boolean
               |  |  +--ro oc-network-instance-ext:max-dynamic-neighbor-prefixes?                                uint16
               |  |  +--ro oc-network-instance-ext:disable-ebgp-connected-route-check?                           boolean
               |  |  +--ro oc-network-instance-ext:fast-external-failover?                                       boolean
               |  |  +--ro oc-network-instance-ext:default-local-preference?                                     uint32
               |  |  +--ro oc-network-instance-ext:route-attribute-entry-count?                                  uint32
               |  |  +--ro oc-network-instance-ext:attribute-database-size?                                      uint64
               |  |  +--ro oc-network-instance-ext:as-path-entry-count?                                        uint32
               |  |  +--ro oc-network-instance-ext:as-path-database-size?                                        uint64
               |  +--rw confederation
               |  |  +--rw config
               |  |  |  +--rw identifier?   oc-inet:as-number
               |  |  |  +--rw member-as*    oc-inet:as-number
               |  |  +--ro state
               |  |     +--ro identifier?   oc-inet:as-number
               |  |     +--ro member-as*    oc-inet:as-number
               |  +--rw graceful-restart
               |  |  +--rw config
               |  |  |  +--rw enabled?                                             boolean
               |  |  |  +--rw restart-time?                                        uint16
               |  |  |  +--rw stale-routes-time?                                   uint16
               |  |  |  +--rw oc-network-instance-ext:preserve-fw-state?                                   boolean
               |  |  |  +--rw oc-network-instance-ext:disable-end-of-rib-marker?                           boolean
               |  |  +--ro state
               |  |     +--ro enabled?                                             boolean
               |  |     +--ro restart-time?                                        uint16
               |  |     +--ro stale-routes-time?                                   uint16
               |  |     +--ro oc-network-instance-ext:preserve-fw-state?                                   boolean
               |  |     +--ro oc-network-instance-ext:disable-end-of-rib-marker?                           boolean
               |  +--rw use-multiple-paths
               |  |  +--rw config
               |  |  +--ro state
               |  |  +--rw ebgp
               |  |     +--rw config
               |  |     |  +--rw allow-multiple-as?                boolean
               |  |     |  +--rw oc-network-instance-ext:as-set?                           boolean
               |  |     +--ro state
               |  |        +--ro allow-multiple-as?                boolean
               |  |        +--ro oc-network-instance-ext:as-set?                           boolean
               |  +--rw route-selection-options
               |  |  +--rw config
               |  |  |  +--rw always-compare-med?                               boolean
               |  |  |  +--rw ignore-as-path-length?                            boolean
               |  |  |  +--rw external-compare-router-id?                       boolean
               |  |  |  +--rw oc-network-instance-ext:network-import-check?                             boolean
               |  |  |  +--rw oc-network-instance-ext:compare-confed-as-path?                           boolean
               |  |  |  +--rw oc-network-instance-ext:deterministic-med?                                boolean
               |  |  |  +--rw oc-network-instance-ext:med-confed?                                       boolean
               |  |  |  +--rw oc-network-instance-ext:med-missing-as-worst?                             boolean
               |  |  +--ro state
               |  |     +--ro always-compare-med?                               boolean
               |  |     +--ro ignore-as-path-length?                            boolean
               |  |     +--ro external-compare-router-id?                       boolean
               |  |     +--ro oc-network-instance-ext:network-import-check?                             boolean
               |  |     +--ro oc-network-instance-ext:compare-confed-as-path?                           boolean
               |  |     +--ro oc-network-instance-ext:deterministic-med?                                boolean
               |  |     +--ro oc-network-instance-ext:med-confed?                                       boolean
               |  |     +--ro oc-network-instance-ext:med-missing-as-worst?                             boolean
               |  +--rw afi-safis
               |  |  +--rw afi-safi* [afi-safi-name]
               |  |     +--rw afi-safi-name                                 -> ../config/afi-safi-name
               |  |     +--rw config
               |  |     |  +--rw afi-safi-name?                                     identityref
               |  |     |  +--rw oc-network-instance-ext:import-policy*                                     -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  |     |  +--rw oc-network-instance-ext:local-route-distance?                              uint8
               |  |     |  +--rw oc-network-instance-ext:external-route-distance?                           uint8
               |  |     |  +--rw oc-network-instance-ext:internal-route-distance?                           uint8
               |  |     +--ro state
               |  |     |  +--ro afi-safi-name?                                     identityref
               |  |     |  +--ro oc-network-instance-ext:import-policy*                                     -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  |     |  +--ro oc-network-instance-ext:local-route-distance?                              uint8
               |  |     |  +--ro oc-network-instance-ext:external-route-distance?                           uint8
               |  |     |  +--ro oc-network-instance-ext:internal-route-distance?                           uint8
               |  |     |  +--ro oc-network-instance-ext:table-version?                                     uint32
               |  |     +--rw use-multiple-paths
               |  |     |  +--rw config
               |  |     |  +--ro state
               |  |     |  +--rw ebgp
               |  |     |  |  +--rw config
               |  |     |  |  |  +--rw maximum-paths?   uint32
               |  |     |  |  +--ro state
               |  |     |  |     +--ro maximum-paths?   uint32
               |  |     |  +--rw ibgp
               |  |     |     +--rw config
               |  |     |     |  +--rw maximum-paths?   uint32
               |  |     |     +--ro state
               |  |     |        +--ro maximum-paths?   uint32
               |  |     +--rw l2vpn-evpn
               |  |     |  +--rw oc-network-instance-ext:config
               |  |     |  |  +--rw oc-network-instance-ext:advertise-all-vni?                         boolean
               |  |     |  |  +--rw oc-network-instance-ext:advertise-ipv4-unicast?                    boolean
               |  |     |  |  +--rw oc-network-instance-ext:advertise-ipv6-unicast?                    boolean
               |  |     |  |  +--rw oc-network-instance-ext:advertise-svi-ip?                          boolean
               |  |     |  |  +--rw oc-network-instance-ext:advertise-default-gateway?                 boolean
               |  |     |  |  +--rw oc-network-instance-ext:disable-ethernet-segment-l3-nexthop-gateway?   boolean
               |  |     |  |  +--rw oc-network-instance-ext:route-distinguisher?                       oc-ni-types:route-distinguisher
               |  |     |  |  +--rw oc-network-instance-ext:auto-route-target?                         enumeration
               |  |     |  |  +--rw oc-network-instance-ext:flooding?                                  enumeration
               |  |     |  |  +--rw oc-network-instance-ext:default-originate-ipv4?                    boolean
               |  |     |  |  +--rw oc-network-instance-ext:default-originate-ipv6?                    boolean
               |  |     |  +--ro oc-network-instance-ext:state
               |  |     |  |  +--ro oc-network-instance-ext:advertise-all-vni?                         boolean
               |  |     |  |  +--ro oc-network-instance-ext:advertise-ipv4-unicast?                    boolean
               |  |     |  |  +--ro oc-network-instance-ext:advertise-ipv6-unicast?                    boolean
               |  |     |  |  +--ro oc-network-instance-ext:advertise-svi-ip?                          boolean
               |  |     |  |  +--ro oc-network-instance-ext:advertise-default-gateway?                 boolean
               |  |     |  |  +--ro oc-network-instance-ext:disable-ethernet-segment-l3-nexthop-gateway?   boolean
               |  |     |  |  +--ro oc-network-instance-ext:route-distinguisher?                       oc-ni-types:route-distinguisher
               |  |     |  |  +--ro oc-network-instance-ext:auto-route-target?                         enumeration
               |  |     |  |  +--ro oc-network-instance-ext:flooding?                                  enumeration
               |  |     |  |  +--ro oc-network-instance-ext:default-originate-ipv4?                    boolean
               |  |     |  |  +--ro oc-network-instance-ext:default-originate-ipv6?                    boolean
               |  |     |  +--rw oc-network-instance-ext:duplicate-address-detection
               |  |     |  |  +--rw oc-network-instance-ext:config
               |  |     |  |  |  +--rw oc-network-instance-ext:enabled?          boolean
               |  |     |  |  |  +--rw oc-network-instance-ext:max-moves?        uint16
               |  |     |  |  |  +--rw oc-network-instance-ext:detection-time?   uint16
               |  |     |  |  |  +--rw oc-network-instance-ext:freeze?           union
               |  |     |  |  +--ro oc-network-instance-ext:state
               |  |     |  |     +--ro oc-network-instance-ext:enabled?          boolean
               |  |     |  |     +--ro oc-network-instance-ext:max-moves?        uint16
               |  |     |  |     +--ro oc-network-instance-ext:detection-time?   uint16
               |  |     |  |     +--ro oc-network-instance-ext:freeze?           union
               |  |     |  +--rw oc-network-instance-ext:route-target
               |  |     |     +--rw oc-network-instance-ext:config
               |  |     |     |  +--rw oc-network-instance-ext:import-route-target*   string
               |  |     |     |  +--rw oc-network-instance-ext:export-route-target*   string
               |  |     |     +--ro oc-network-instance-ext:state
               |  |     |        +--ro oc-network-instance-ext:import-route-target*   string
               |  |     |        +--ro oc-network-instance-ext:export-route-target*   string
               |  |     +--rw oc-network-instance-ext:import-sources
               |  |     |  +--rw oc-network-instance-ext:import-source* [source-network-instance]
               |  |     |     +--rw oc-network-instance-ext:source-network-instance    -> ../config/source-network-instance
               |  |     |     +--rw oc-network-instance-ext:config
               |  |     |     |  +--rw oc-network-instance-ext:source-network-instance?   -> /oc-netinst:network-instances/network-instance/name
               |  |     |     |  +--rw oc-network-instance-ext:import-policy?             -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  |     |     +--ro oc-network-instance-ext:state
               |  |     |        +--ro oc-network-instance-ext:source-network-instance?   -> /oc-netinst:network-instances/network-instance/name
               |  |     |        +--ro oc-network-instance-ext:import-policy?             -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  |     +--rw oc-network-instance-ext:route-flap-damping
               |  |     |  +--rw oc-network-instance-ext:config
               |  |     |  |  +--rw oc-network-instance-ext:enabled?              boolean
               |  |     |  |  +--rw oc-network-instance-ext:half-life?            uint8
               |  |     |  |  +--rw oc-network-instance-ext:reuse-threshold?      uint16
               |  |     |  |  +--rw oc-network-instance-ext:suppress-threshold?   uint16
               |  |     |  |  +--rw oc-network-instance-ext:max-suppress?         uint8
               |  |     |  +--ro oc-network-instance-ext:state
               |  |     |     +--ro oc-network-instance-ext:enabled?              boolean
               |  |     |     +--ro oc-network-instance-ext:half-life?            uint8
               |  |     |     +--ro oc-network-instance-ext:reuse-threshold?      uint16
               |  |     |     +--ro oc-network-instance-ext:suppress-threshold?   uint16
               |  |     |     +--ro oc-network-instance-ext:max-suppress?         uint8
               |  |     +--rw oc-network-instance-ext:networks
               |  |        +--rw oc-network-instance-ext:network* [prefix]
               |  |           +--rw oc-network-instance-ext:prefix          -> ../config/prefix
               |  |           +--rw oc-network-instance-ext:config
               |  |           |  +--rw oc-network-instance-ext:prefix?     inet:ip-prefix
               |  |           |  +--rw oc-network-instance-ext:backdoor?   boolean
               |  |           +--ro oc-network-instance-ext:state
               |  |           |  +--ro oc-network-instance-ext:prefix?     inet:ip-prefix
               |  |           |  +--ro oc-network-instance-ext:backdoor?   boolean
               |  |           +--rw oc-network-instance-ext:apply-policy
               |  |              +--rw oc-network-instance-ext:config
               |  |              |  +--rw oc-network-instance-ext:export-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  |              +--ro oc-network-instance-ext:state
               |  |                 +--ro oc-network-instance-ext:export-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |  +--rw dynamic-neighbor-prefixes
               |  |  +--rw dynamic-neighbor-prefix* [prefix]
               |  |     +--rw prefix    -> ../config/prefix
               |  |     +--rw config
               |  |     |  +--rw prefix?       oc-inet:ip-prefix
               |  |     |  +--rw peer-group?   -> ../../../../../peer-groups/peer-group/config/peer-group-name
               |  |     +--ro state
               |  |        +--ro prefix?       oc-inet:ip-prefix
               |  |        +--ro peer-group?   -> ../../../../../peer-groups/peer-group/config/peer-group-name
               |  +--rw apply-policy
               |  |  +--rw config
               |  |  |  +--rw oc-network-instance-ext:ebgp-requires-policy?   boolean
               |  |  +--ro state
               |  |     +--ro oc-network-instance-ext:ebgp-requires-policy?   boolean
               |  +--rw oc-network-instance-ext:logging-options
               |  |  +--rw oc-network-instance-ext:config
               |  |  |  +--rw oc-network-instance-ext:log-neighbor-state-changes?   boolean
               |  |  +--ro oc-network-instance-ext:state
               |  |     +--ro oc-network-instance-ext:log-neighbor-state-changes?   boolean
               |  +--rw oc-network-instance-ext:timers
               |  |  +--rw oc-network-instance-ext:config
               |  |  |  +--rw oc-network-instance-ext:hold-time?            uint16
               |  |  |  +--rw oc-network-instance-ext:keepalive-interval?   uint16
               |  |  +--ro oc-network-instance-ext:state
               |  |     +--ro oc-network-instance-ext:hold-time?            uint16
               |  |     +--ro oc-network-instance-ext:keepalive-interval?   uint16
               |  +--rw oc-network-instance-ext:bgp-ext-config
               |  |  +--rw oc-network-instance-ext:config
               |  |  |  +--rw oc-network-instance-ext:read-quanta?               uint8
               |  |  |  +--rw oc-network-instance-ext:write-quanta?              uint8
               |  |  |  +--rw oc-network-instance-ext:coalesce-time?             uint32
               |  |  |  +--rw oc-network-instance-ext:show-hostname?             boolean
               |  |  |  +--rw oc-network-instance-ext:shutdown?                  boolean
               |  |  |  +--rw oc-network-instance-ext:subgroup-pkt-queue-max?    uint8
               |  |  |  +--rw oc-network-instance-ext:max-delay?                 uint16
               |  |  |  +--rw oc-network-instance-ext:establish-wait?            uint16
               |  |  |  +--rw oc-network-instance-ext:route-map-process-delay?   uint16
               |  |  +--ro oc-network-instance-ext:state
               |  |     +--ro oc-network-instance-ext:read-quanta?               uint8
               |  |     +--ro oc-network-instance-ext:write-quanta?              uint8
               |  |     +--ro oc-network-instance-ext:coalesce-time?             uint32
               |  |     +--ro oc-network-instance-ext:show-hostname?             boolean
               |  |     +--ro oc-network-instance-ext:shutdown?                  boolean
               |  |     +--ro oc-network-instance-ext:subgroup-pkt-queue-max?    uint8
               |  |     +--ro oc-network-instance-ext:max-delay?                 uint16
               |  |     +--ro oc-network-instance-ext:establish-wait?            uint16
               |  |     +--ro oc-network-instance-ext:route-map-process-delay?   uint16
               |  +--rw oc-network-instance-ext:max-med
               |  |  +--rw oc-network-instance-ext:config
               |  |  |  +--rw oc-network-instance-ext:max-med-time?        uint32
               |  |  |  +--rw oc-network-instance-ext:max-med-val?         uint32
               |  |  |  +--rw oc-network-instance-ext:max-med-admin?       boolean
               |  |  |  +--rw oc-network-instance-ext:max-med-admin-val?   uint32
               |  |  +--ro oc-network-instance-ext:state
               |  |     +--ro oc-network-instance-ext:max-med-time?        uint32
               |  |     +--ro oc-network-instance-ext:max-med-val?         uint32
               |  |     +--ro oc-network-instance-ext:max-med-admin?       boolean
               |  |     +--ro oc-network-instance-ext:max-med-admin-val?   uint32
               |  +--rw oc-network-instance-ext:route-reflector
               |  |  +--rw oc-network-instance-ext:config
               |  |  |  +--rw oc-network-instance-ext:route-reflector-cluster-id?    oc-bgp-types:rr-cluster-id-type
               |  |  |  +--rw oc-network-instance-ext:allow-out-policy?              boolean
               |  |  |  +--rw oc-network-instance-ext:client-to-client-reflection?   boolean
               |  |  +--ro oc-network-instance-ext:state
               |  |     +--ro oc-network-instance-ext:route-reflector-cluster-id?    oc-bgp-types:rr-cluster-id-type
               |  |     +--ro oc-network-instance-ext:allow-out-policy?              boolean
               |  |     +--ro oc-network-instance-ext:client-to-client-reflection?   boolean
               |  +--rw oc-network-instance-ext:graceful-shutdown
               |     +--rw oc-network-instance-ext:config
               |     |  +--rw oc-network-instance-ext:enabled?   boolean
               |     +--ro oc-network-instance-ext:state
               |        +--ro oc-network-instance-ext:enabled?   boolean
               +--rw neighbors
               |  +--rw neighbor* [neighbor-address]
               |     +--rw neighbor-address    -> ../config/neighbor-address
               |     +--rw config
               |     |  +--rw peer-group?                                                   -> ../../../../peer-groups/peer-group/peer-group-name
               |     |  +--rw neighbor-address?                                             union
               |     |  +--rw neighbor-port?                                                oc-inet:port-number
               |     |  +--rw enabled?                                                      boolean
               |     |  +--rw peer-as?                                                      oc-inet:as-number
               |     |  +--rw local-as?                                                     oc-inet:as-number
               |     |  +--rw peer-type?                                                    oc-bgp-types:peer-type
               |     |  +--rw auth-password?                                                oc-types:routing-password
               |     |  +--rw description?                                                  string
               |     |  +--rw oc-network-instance-ext:disable-ebgp-connected-route-check?                           boolean
               |     |  +--rw oc-network-instance-ext:extended-next-hop-encoding?                                   boolean
               |     |  +--rw oc-network-instance-ext:solo-peer?                                                    boolean
               |     |  +--rw oc-network-instance-ext:ttl-security-hops?                                            uint8
               |     |  +--rw oc-network-instance-ext:dynamic-capability-negotiation?                                boolean
               |     |  +--rw oc-network-instance-ext:disable-capability-negotiation?                                boolean
               |     |  +--rw oc-network-instance-ext:override-capability?                                         boolean
               |     |  +--rw oc-network-instance-ext:strict-capability-match?                                       boolean
               |     |  +--rw oc-network-instance-ext:shutdown-message?                                              string
               |     +--ro state
               |     |  +--ro peer-group?                                                   -> ../../../../peer-groups/peer-group/peer-group-name
               |     |  +--ro neighbor-address?                                             union
               |     |  +--ro neighbor-port?                                                oc-inet:port-number
               |     |  +--ro enabled?                                                      boolean
               |     |  +--ro peer-as?                                                      oc-inet:as-number
               |     |  +--ro local-as?                                                     oc-inet:as-number
               |     |  +--ro peer-type?                                                    oc-bgp-types:peer-type
               |     |  +--ro auth-password?                                                oc-types:routing-password
               |     |  +--ro description?                                                  string
               |     |  +--ro session-state?                                                enumeration
               |     |  +--ro last-established?                                             oc-types:timeticks64
               |     |  +--ro messages
               |     |  |  +--ro sent
               |     |  |  |  +--ro last-notification-time?                  oc-types:timeticks64
               |     |  |  |  +--ro last-notification-error-code?            identityref
               |     |  |  |  +--ro last-notification-error-subcode?         identityref
               |     |  |  |  +--ro oc-network-instance-ext:KEEPALIVE?                                 uint64
               |     |  |  |  +--ro oc-network-instance-ext:ROUTE-REFRESH?                             uint64
               |     |  |  +--ro received
               |     |  |     +--ro last-notification-time?                  oc-types:timeticks64
               |     |  |     +--ro last-notification-error-code?            identityref
               |     |  |     +--ro last-notification-error-subcode?         identityref
               |     |  |     +--ro oc-network-instance-ext:KEEPALIVE?                                 uint64
               |     |  |     +--ro oc-network-instance-ext:ROUTE-REFRESH?                             uint64
               |     |  +--ro oc-network-instance-ext:disable-ebgp-connected-route-check?            boolean
               |     |  +--ro oc-network-instance-ext:extended-next-hop-encoding?                      boolean
               |     |  +--ro oc-network-instance-ext:solo-peer?                                         boolean
               |     |  +--ro oc-network-instance-ext:ttl-security-hops?                                 uint8
               |     |  +--ro oc-network-instance-ext:dynamic-capability-negotiation?                    boolean
               |     |  +--ro oc-network-instance-ext:disable-capability-negotiation?                    boolean
               |     |  +--ro oc-network-instance-ext:override-capability?                               boolean
               |     |  +--ro oc-network-instance-ext:strict-capability-match?                           boolean
               |     |  +--ro oc-network-instance-ext:shutdown-message?                                  string
               |     |  +--ro oc-network-instance-ext:received-prefixes-count?                           uint32
               |     |  +--ro oc-network-instance-ext:advertised-capability?                             string
               |     |  +--ro oc-network-instance-ext:received-capability?                               string
               |     |  +--ro oc-network-instance-ext:last-flap-timestamp?                               string
               |     |  +--ro oc-network-instance-ext:remote-router-id?                                  oc-yang:dotted-quad
               |     +--rw timers
               |     |  +--rw config
               |     |  |  +--rw connect-retry?                    uint16
               |     |  |  +--rw hold-time?                        uint16
               |     |  |  +--rw keepalive-interval?               uint16
               |     |  |  +--rw minimum-advertisement-interval?   uint16
               |     |  +--ro state
               |     |     +--ro connect-retry?                    uint16
               |     |     +--ro hold-time?                        uint16
               |     |     +--ro keepalive-interval?               uint16
               |     |     +--ro minimum-advertisement-interval?   uint16
               |     +--rw transport
               |     |  +--rw config
               |     |  |  +--rw tcp-mss?         uint16
               |     |  |  +--rw passive-mode?    boolean
               |     |  |  +--rw local-address?   union
               |     |  +--ro state
               |     |     +--ro tcp-mss?                            uint16
               |     |     +--ro passive-mode?                       boolean
               |     |     +--ro local-address?                      union
               |     |     +--ro local-port?                         oc-inet:port-number
               |     |     +--ro remote-address?                     oc-inet:ip-address
               |     |     +--ro remote-port?                        oc-inet:port-number
               |     |     +--ro oc-network-instance-ext:local-ip?                           inet:ip-address
               |     +--rw ebgp-multihop
               |     |  +--rw config
               |     |  |  +--rw enabled?                                    boolean
               |     |  |  +--rw multihop-ttl?                               uint8
               |     |  |  +--rw oc-network-instance-ext:enforce-multihop?                           boolean
               |     |  +--ro state
               |     |     +--ro enabled?                                    boolean
               |     |     +--ro multihop-ttl?                               uint8
               |     |     +--ro oc-network-instance-ext:enforce-multihop?                           boolean
               |     +--rw as-path-options
               |     |  +--rw config
               |     |  |  +--rw oc-network-instance-ext:enforce-first-as?      boolean
               |     |  |  +--rw oc-network-instance-ext:local-as-no-prepend?   boolean
               |     |  |  +--rw oc-network-instance-ext:local-as-replace-as?   boolean
               |     |  +--ro state
               |     |     +--ro oc-network-instance-ext:enforce-first-as?      boolean
               |     |     +--ro oc-network-instance-ext:local-as-no-prepend?   boolean
               |     |     +--ro oc-network-instance-ext:local-as-replace-as?   boolean
               |     +--rw afi-safis
               |     |  +--rw afi-safi* [afi-safi-name]
               |     |     +--rw afi-safi-name    -> ../config/afi-safi-name
               |     |     +--rw config
               |     |     |  +--rw afi-safi-name?                                                 identityref
               |     |     |  +--rw enabled?                                                       boolean
               |     |     |  +--rw send-community-type*                                           oc-bgp-types:community-type
               |     |     |  +--rw oc-network-instance-ext:soft-reconfiguration-inbound?          boolean
               |     |     |  +--rw oc-network-instance-ext:replace-peer-as?                       boolean
               |     |     |  +--rw oc-network-instance-ext:route-server-client?                   boolean
               |     |     |  +--rw oc-network-instance-ext:outbound-route-filtering-capability?   enumeration
               |     |     |  +--rw oc-network-instance-ext:weight?                                uint16
               |     |     |  +--rw oc-network-instance-ext:route-reflector-client?                boolean
               |     |     +--ro state
               |     |     |  +--ro afi-safi-name?                                                 identityref
               |     |     |  +--ro enabled?                                                       boolean
               |     |     |  +--ro send-community-type*                                           oc-bgp-types:community-type
               |     |     |  +--ro prefixes
               |     |     |  |  +--ro received?                          uint32
               |     |     |  |  +--ro received-pre-policy?               uint32
               |     |     |  |  +--ro sent?                              uint32
               |     |     |  |  +--ro installed?                         uint32
               |     |     |  |  +--ro oc-network-instance-ext:flushed?                           uint32
               |     |     |  +--ro oc-network-instance-ext:soft-reconfiguration-inbound?          boolean
               |     |     |  +--ro oc-network-instance-ext:replace-peer-as?                       boolean
               |     |     |  +--ro oc-network-instance-ext:route-server-client?                   boolean
               |     |     |  +--ro oc-network-instance-ext:outbound-route-filtering-capability?   enumeration
               |     |     |  +--ro oc-network-instance-ext:weight?                                uint16
               |     |     |  +--ro oc-network-instance-ext:route-reflector-client?                boolean
               |     |     |  +--ro oc-network-instance-ext:table-version?                         uint64
               |     |     |  +--ro oc-network-instance-ext:peer-table-version?                    uint32
               |     |     |  +--ro oc-network-instance-ext:accepted-path-count?                   uint32
               |     |     +--rw add-paths
               |     |     |  +--rw config
               |     |     |  |  +--rw send?                                            boolean
               |     |     |  |  +--rw send-max?                                        uint8
               |     |     |  |  +--rw oc-network-instance-ext:send-best-path-per-as?   boolean
               |     |     |  +--ro state
               |     |     |     +--ro send?                                            boolean
               |     |     |     +--ro send-max?                                        uint8
               |     |     |     +--ro oc-network-instance-ext:send-best-path-per-as?   boolean
               |     |     +--rw apply-policy
               |     |     |  +--rw config
               |     |     |  |  +--rw import-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |  |  +--rw export-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |  |  +--rw oc-network-instance-ext:import-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
               |     |     |  |  +--rw oc-network-instance-ext:export-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
               |     |     |  |  +--rw oc-network-instance-ext:import-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
               |     |     |  |  +--rw oc-network-instance-ext:export-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
               |     |     |  |  +--rw oc-network-instance-ext:default-originate-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |  |  +--rw oc-network-instance-ext:unsuppress-map-policy?      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |  |  +--rw oc-network-instance-ext:next-hop-self?              boolean
               |     |     |  |  +--rw oc-network-instance-ext:next-hop-self-force?        boolean
               |     |     |  +--ro state
               |     |     |     +--ro import-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |     +--ro export-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |     +--ro oc-network-instance-ext:import-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
               |     |     |     +--ro oc-network-instance-ext:export-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
               |     |     |     +--ro oc-network-instance-ext:import-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
               |     |     |     +--ro oc-network-instance-ext:export-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
               |     |     |     +--ro oc-network-instance-ext:default-originate-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |     +--ro oc-network-instance-ext:unsuppress-map-policy?      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
               |     |     |     +--ro oc-network-instance-ext:next-hop-self?              boolean
               |     |     |     +--ro oc-network-instance-ext:next-hop-self-force?        boolean
               |     |     +--rw ipv4-unicast
               |     |     |  +--rw prefix-limit
               |     |     |  |  +--rw config
               |     |     |  |  |  +--rw max-prefixes?                           uint32
               |     |     |  |  |  +--rw prevent-teardown?                       boolean
               |     |     |  |  |  +--rw warning-threshold-pct?                  oc-types:percentage
               |     |     |  |  |  +--rw oc-network-instance-ext:restart-time?   uint16
               |     |     |  |  +--ro state
               |     |     |  |     +--ro max-prefixes?                           uint32
               |     |     |  |     +--ro prevent-teardown?                       boolean
               |     |     |  |     +--ro warning-threshold-pct?                  oc-types:percentage
               |     |     |  |     +--ro oc-network-instance-ext:restart-time?   uint16
               |     |     |  +--rw config
               |     |     |  |  +--rw send-default-route?   boolean
               |     |     |  +--ro state
               |     |     |     +--ro send-default-route?   boolean
               |     |     +--rw ipv6-unicast
               |     |     |  +--rw prefix-limit
               |     |     |  |  +--rw config
               |     |     |  |  |  +--rw max-prefixes?                           uint32
               |     |     |  |  |  +--rw prevent-teardown?                       boolean
               |     |     |  |  |  +--rw warning-threshold-pct?                  oc-types:percentage
               |     |     |  |  |  +--rw oc-network-instance-ext:restart-time?   uint16
               |     |     |  |  +--ro state
               |     |     |  |     +--ro max-prefixes?                           uint32
               |     |     |  |     +--ro prevent-teardown?                       boolean
               |     |     |  |     +--ro warning-threshold-pct?                  oc-types:percentage
               |     |     |  |     +--ro oc-network-instance-ext:restart-time?   uint16
               |     |     |  +--rw config
               |     |     |  |  +--rw send-default-route?   boolean
               |     |     |  +--ro state
               |     |     |     +--ro send-default-route?   boolean
               |     |     +--rw oc-network-instance-ext:allow-own-as
               |     |     |  +--rw oc-network-instance-ext:config
               |     |     |  |  +--rw oc-network-instance-ext:enabled?    boolean
               |     |     |  |  +--rw oc-network-instance-ext:as-count?   uint8
               |     |     |  |  +--rw oc-network-instance-ext:origin?     boolean
               |     |     |  +--ro oc-network-instance-ext:state
               |     |     |     +--ro oc-network-instance-ext:enabled?    boolean
               |     |     |     +--ro oc-network-instance-ext:as-count?   uint8
               |     |     |     +--ro oc-network-instance-ext:origin?     boolean
               |     |     +--rw oc-network-instance-ext:remove-private-as
               |     |     |  +--rw oc-network-instance-ext:config
               |     |     |  |  +--rw oc-network-instance-ext:enabled?              boolean
               |     |     |  |  +--rw oc-network-instance-ext:all?                  boolean
               |     |     |  |  +--rw oc-network-instance-ext:replace-private-as?   boolean
               |     |     |  +--ro oc-network-instance-ext:state
               |     |     |     +--ro oc-network-instance-ext:enabled?              boolean
               |     |     |     +--ro oc-network-instance-ext:all?                  boolean
               |     |     |     +--ro oc-network-instance-ext:replace-private-as?   boolean
               |     |     +--rw oc-network-instance-ext:attribute-transparency
               |     |        +--rw oc-network-instance-ext:config
               |     |        |  +--rw oc-network-instance-ext:preserve-as-path-enabled?    boolean
               |     |        |  +--rw oc-network-instance-ext:preserve-med-enabled?        boolean
               |     |        |  +--rw oc-network-instance-ext:preserve-next-hop-enabled?   boolean
               |     |        +--ro oc-network-instance-ext:state
               |     |           +--ro oc-network-instance-ext:preserve-as-path-enabled?    boolean
               |     |           +--ro oc-network-instance-ext:preserve-med-enabled?        boolean
               |     |           +--ro oc-network-instance-ext:preserve-next-hop-enabled?   boolean
               |     +--rw enable-bfd
               |        +--rw config
               |        |  +--rw enabled?                                               boolean
               |        |  +--rw desired-minimum-tx-interval?                           uint32
               |        |  +--rw required-minimum-receive?                              uint32
               |        |  +--rw detection-multiplier?                                  uint8
               |        |  +--rw oc-network-instance-ext:check-control-plane-failure?                           boolean
               |        |  +--rw oc-network-instance-ext:strict-mode?                                           boolean
               |        +--ro state
               |           +--ro enabled?                                               boolean
               |           +--ro desired-minimum-tx-interval?                           uint32
               |           +--ro required-minimum-receive?                              uint32
               |           +--ro detection-multiplier?                                  uint8
               |           +--ro oc-network-instance-ext:check-control-plane-failure?                           boolean
               |           +--ro oc-network-instance-ext:strict-mode?                                           boolean
               +--rw peer-groups
                  +--rw peer-group* [peer-group-name]
                     +--rw peer-group-name     -> ../config/peer-group-name
                     +--rw config
                     |  +--rw peer-group-name?                                              string
                     |  +--rw peer-as?                                                      oc-inet:as-number
                     |  +--rw local-as?                                                     oc-inet:as-number
                     |  +--rw peer-type?                                                    oc-bgp-types:peer-type
                     |  +--rw auth-password?                                                oc-types:routing-password
                     |  +--rw description?                                                  string
                     |  +--rw oc-network-instance-ext:enabled?                                                      boolean
                     |  +--rw oc-network-instance-ext:neighbor-port?                                                oc-inet:port-number
                     |  +--rw oc-network-instance-ext:disable-ebgp-connected-route-check?                           boolean
                     |  +--rw oc-network-instance-ext:extended-next-hop-encoding?                                   boolean
                     |  +--rw oc-network-instance-ext:solo-peer?                                                    boolean
                     |  +--rw oc-network-instance-ext:ttl-security-hops?                                            uint8
                     |  +--rw oc-network-instance-ext:dynamic-capability-negotiation?                                boolean
                     |  +--rw oc-network-instance-ext:disable-capability-negotiation?                                boolean
                     |  +--rw oc-network-instance-ext:override-capability?                                          boolean
                     |  +--rw oc-network-instance-ext:strict-capability-match?                                       boolean
                     |  +--rw oc-network-instance-ext:shutdown-message?                                              string
                     +--ro state
                     |  +--ro peer-group-name?                                              string
                     |  +--ro peer-as?                                                      oc-inet:as-number
                     |  +--ro local-as?                                                     oc-inet:as-number
                     |  +--ro peer-type?                                                    oc-bgp-types:peer-type
                     |  +--ro auth-password?                                                oc-types:routing-password
                     |  +--ro description?                                                  string
                     |  +--ro oc-network-instance-ext:enabled?                                                      boolean
                     |  +--ro oc-network-instance-ext:neighbor-port?                                                oc-inet:port-number
                     |  +--ro oc-network-instance-ext:disable-ebgp-connected-route-check?                           boolean
                     |  +--ro oc-network-instance-ext:extended-next-hop-encoding?                                   boolean
                     |  +--ro oc-network-instance-ext:solo-peer?                                                    boolean
                     |  +--ro oc-network-instance-ext:ttl-security-hops?                                            uint8
                     |  +--ro oc-network-instance-ext:dynamic-capability-negotiation?                                boolean
                     |  +--ro oc-network-instance-ext:disable-capability-negotiation?                                boolean
                     |  +--ro oc-network-instance-ext:override-capability?                                          boolean
                     |  +--ro oc-network-instance-ext:strict-capability-match?                                       boolean
                     |  +--ro oc-network-instance-ext:shutdown-message?                                              string
                     +--rw timers
                     |  +--rw config
                     |  |  +--rw connect-retry?                    uint16
                     |  |  +--rw hold-time?                        uint16
                     |  |  +--rw keepalive-interval?               uint16
                     |  |  +--rw minimum-advertisement-interval?   uint16
                     |  +--ro state
                     |     +--ro connect-retry?                    uint16
                     |     +--ro hold-time?                        uint16
                     |     +--ro keepalive-interval?               uint16
                     |     +--ro minimum-advertisement-interval?   uint16
                     +--rw transport
                     |  +--rw config
                     |  |  +--rw tcp-mss?         uint16
                     |  |  +--rw passive-mode?    boolean
                     |  |  +--rw local-address?   union
                     |  +--ro state
                     |     +--ro tcp-mss?         uint16
                     |     +--ro passive-mode?    boolean
                     |     +--ro local-address?   union
                     +--rw graceful-restart
                     |  +--rw config
                     |  |  +--rw enabled?   boolean
                     |  +--ro state
                     |     +--ro enabled?   boolean
                     +--rw ebgp-multihop
                     |  +--rw config
                     |  |  +--rw enabled?                                    boolean
                     |  |  +--rw multihop-ttl?                               uint8
                     |  |  +--rw oc-network-instance-ext:enforce-multihop?                           boolean
                     |  +--ro state
                     |     +--ro enabled?                                    boolean
                     |     +--ro multihop-ttl?                               uint8
                     |     +--ro oc-network-instance-ext:enforce-multihop?                           boolean
                     +--rw as-path-options
                     |  +--rw config
                     |  |  +--rw oc-network-instance-ext:enforce-first-as?      boolean
                     |  |  +--rw oc-network-instance-ext:local-as-no-prepend?   boolean
                     |  |  +--rw oc-network-instance-ext:local-as-replace-as?   boolean
                     |  +--ro state
                     |     +--ro oc-network-instance-ext:enforce-first-as?      boolean
                     |     +--ro oc-network-instance-ext:local-as-no-prepend?   boolean
                     |     +--ro oc-network-instance-ext:local-as-replace-as?   boolean
                     +--rw afi-safis
                     |  +--rw afi-safi* [afi-safi-name]
                     |     +--rw afi-safi-name    -> ../config/afi-safi-name
                     |     +--rw config
                     |     |  +--rw afi-safi-name?                                                 identityref
                     |     |  +--rw enabled?                                                       boolean
                     |     |  +--rw send-community-type*                                           oc-bgp-types:community-type
                     |     |  +--rw oc-network-instance-ext:soft-reconfiguration-inbound?          boolean
                     |     |  +--rw oc-network-instance-ext:replace-peer-as?                       boolean
                     |     |  +--rw oc-network-instance-ext:route-server-client?                   boolean
                     |     |  +--rw oc-network-instance-ext:outbound-route-filtering-capability?   enumeration
                     |     |  +--rw oc-network-instance-ext:weight?                                uint16
                     |     |  +--rw oc-network-instance-ext:route-reflector-client?                boolean
                     |     +--ro state
                     |     |  +--ro afi-safi-name?                                                 identityref
                     |     |  +--ro enabled?                                                       boolean
                     |     |  +--ro send-community-type*                                           oc-bgp-types:community-type
                     |     |  +--ro oc-network-instance-ext:soft-reconfiguration-inbound?          boolean
                     |     |  +--ro oc-network-instance-ext:replace-peer-as?                       boolean
                     |     |  +--ro oc-network-instance-ext:route-server-client?                   boolean
                     |     |  +--ro oc-network-instance-ext:outbound-route-filtering-capability?   enumeration
                     |     |  +--ro oc-network-instance-ext:weight?                                uint16
                     |     |  +--ro oc-network-instance-ext:route-reflector-client?                boolean
                     |     +--rw add-paths
                     |     |  +--rw config
                     |     |  |  +--rw send?                                            boolean
                     |     |  |  +--rw send-max?                                        uint8
                     |     |  |  +--rw oc-network-instance-ext:send-best-path-per-as?   boolean
                     |     |  +--ro state
                     |     |     +--ro send?                                            boolean
                     |     |     +--ro send-max?                                        uint8
                     |     |     +--ro oc-network-instance-ext:send-best-path-per-as?   boolean
                     |     +--rw apply-policy
                     |        +--rw config
                     |        |  +--rw import-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |        |  +--rw export-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |        |  +--rw oc-network-instance-ext:import-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
                     |        |  +--rw oc-network-instance-ext:export-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
                     |        |  +--rw oc-network-instance-ext:import-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
                     |        |  +--rw oc-network-instance-ext:export-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
                     |        |  +--rw oc-network-instance-ext:default-originate-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |        |  +--rw oc-network-instance-ext:unsuppress-map-policy?      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |        |  +--rw oc-network-instance-ext:next-hop-self?              boolean
                     |        |  +--rw oc-network-instance-ext:next-hop-self-force?        boolean
                     |        +--ro state
                     |           +--ro import-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |           +--ro export-policy*                                      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |           +--ro oc-network-instance-ext:import-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
                     |           +--ro oc-network-instance-ext:export-as-path-set?         -> /oc-rpol:routing-policy/defined-sets/oc-bgp-pol:bgp-defined-sets/as-path-sets/as-path-set/as-path-set-name
                     |           +--ro oc-network-instance-ext:import-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
                     |           +--ro oc-network-instance-ext:export-prefix-set?          -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
                     |           +--ro oc-network-instance-ext:default-originate-policy?   -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |           +--ro oc-network-instance-ext:unsuppress-map-policy?      -> /oc-rpol:routing-policy/policy-definitions/policy-definition/name
                     |           +--ro oc-network-instance-ext:next-hop-self?              boolean
                     |           +--ro oc-network-instance-ext:next-hop-self-force?        boolean
                     |     +--rw ipv4-unicast
                     |     |  +--rw prefix-limit
                     |     |  |  +--rw config
                     |     |  |  |  +--rw max-prefixes?                           uint32
                     |     |  |  |  +--rw prevent-teardown?                       boolean
                     |     |  |  |  +--rw warning-threshold-pct?                  oc-types:percentage
                     |     |  |  |  +--rw oc-network-instance-ext:restart-time?   uint16
                     |     |  |  +--ro state
                     |     |  |     +--ro max-prefixes?                           uint32
                     |     |  |     +--ro prevent-teardown?                       boolean
                     |     |  |     +--ro warning-threshold-pct?                  oc-types:percentage
                     |     |  |     +--ro oc-network-instance-ext:restart-time?   uint16
                     |     |  +--rw config
                     |     |  |  +--rw send-default-route?   boolean
                     |     |  +--ro state
                     |     |     +--ro send-default-route?   boolean
                     |     +--rw ipv6-unicast
                     |     |  +--rw prefix-limit
                     |     |  |  +--rw config
                     |     |  |  |  +--rw max-prefixes?                           uint32
                     |     |  |  |  +--rw prevent-teardown?                       boolean
                     |     |  |  |  +--rw warning-threshold-pct?                  oc-types:percentage
                     |     |  |  |  +--rw oc-network-instance-ext:restart-time?   uint16
                     |     |  |  +--ro state
                     |     |  |     +--ro max-prefixes?                           uint32
                     |     |  |     +--ro prevent-teardown?                       boolean
                     |     |  |     +--ro warning-threshold-pct?                  oc-types:percentage
                     |     |  |     +--ro oc-network-instance-ext:restart-time?   uint16
                     |     |  +--rw config
                     |     |  |  +--rw send-default-route?   boolean
                     |     |  +--ro state
                     |     |     +--ro send-default-route?   boolean
                     |     +--rw oc-network-instance-ext:allow-own-as
                     |        +--rw oc-network-instance-ext:config
                     |        |  +--rw oc-network-instance-ext:enabled?    boolean
                     |        |  +--rw oc-network-instance-ext:as-count?   uint8
                     |        |  +--rw oc-network-instance-ext:origin?     boolean
                     |        +--ro oc-network-instance-ext:state
                     |           +--ro oc-network-instance-ext:enabled?    boolean
                     |           +--ro oc-network-instance-ext:as-count?   uint8
                     |           +--ro oc-network-instance-ext:origin?     boolean
                     |     +--rw oc-network-instance-ext:remove-private-as
                     |        +--rw oc-network-instance-ext:config
                     |        |  +--rw oc-network-instance-ext:enabled?              boolean
                     |        |  +--rw oc-network-instance-ext:all?                  boolean
                     |        |  +--rw oc-network-instance-ext:replace-private-as?   boolean
                     |        +--ro oc-network-instance-ext:state
                     |           +--ro oc-network-instance-ext:enabled?              boolean
                     |           +--ro oc-network-instance-ext:all?                  boolean
                     |           +--ro oc-network-instance-ext:replace-private-as?   boolean
                     |     +--rw oc-network-instance-ext:attribute-transparency
                     |        +--rw oc-network-instance-ext:config
                     |        |  +--rw oc-network-instance-ext:preserve-as-path-enabled?    boolean
                     |        |  +--rw oc-network-instance-ext:preserve-med-enabled?        boolean
                     |        |  +--rw oc-network-instance-ext:preserve-next-hop-enabled?   boolean
                     |        +--ro oc-network-instance-ext:state
                     |           +--ro oc-network-instance-ext:preserve-as-path-enabled?    boolean
                     |           +--ro oc-network-instance-ext:preserve-med-enabled?        boolean
                     |           +--ro oc-network-instance-ext:preserve-next-hop-enabled?   boolean
                     +--rw enable-bfd
                        +--rw config
                        |  +--rw enabled?                                               boolean
                        |  +--rw desired-minimum-tx-interval?                           uint32
                        |  +--rw required-minimum-receive?                              uint32
                        |  +--rw detection-multiplier?                                  uint8
                        |  +--rw oc-network-instance-ext:check-control-plane-failure?                           boolean
                        |  +--rw oc-network-instance-ext:strict-mode?                                           boolean
                        +--ro state
                           +--ro enabled?                                               boolean
                           +--ro desired-minimum-tx-interval?                           uint32
                           +--ro required-minimum-receive?                              uint32
                           +--ro detection-multiplier?                                  uint8
                           +--ro oc-network-instance-ext:check-control-plane-failure?                           boolean
                           +--ro oc-network-instance-ext:strict-mode?                                           boolean
```

Extension leaves are documented in [Section 3.1.5 OpenConfig Extensions](#315-openconfig-extensions).

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term** | **Definition** |
|--------------------------|-------------------------------------|
| YANG | Yet Another Next Generation: modular language representing data structures in an XML tree format |
| gNMI | gRPC Network Management Interface |
| BGP | Border Gateway Protocol |
| VRF | Virtual Routing and Forwarding |
| AFI | Address Family Identifier |
| SAFI | Subsequent Address Family Identifier |
| BFD | Bidirectional Forwarding Detection |
| AS | Autonomous System |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Support BGP protocol configuration within network instances.
2. Support BGP global configuration (AS number, router-id, graceful restart, timers, confederation, route-reflector, max-med, graceful-shutdown).
3. Support BGP global AFI-SAFI configuration (multi-path, route-flap-damping, import-sources, l2vpn-evpn, networks).
4. Support BGP neighbor configuration (address, peer-as, timers, transport, AFI-SAFIs with apply-policy, BFD, extension leaves).
5. Support BGP peer-group configuration (timers, transport, graceful-restart, ebgp-multihop, as-path-options, AFI-SAFIs, BFD).
6. Support dynamic neighbor prefixes.
7. Support local aggregate routes under `protocol[identifier=LOCAL_AGGREGATE][name=bgp]/local-aggregates` (prefix, summary-only, as-set, export-policy).
8. Support table connections for route redistribution between protocols (`DIRECTLY_CONNECTED→BGP`, `STATIC→BGP`; `LOCAL_AGGREGATE→BGP` is GET-only).
9. Support operational GET for routing `tables` per protocol and address family.
10. Support extended BGP global features (confederation, route-reflector, max-med, graceful-shutdown, route-flap-damping, l2vpn-evpn).
11. Provide Get, Patch, and Delete operations via REST and gNMI.
12. Provide gNMI Subscribe for BGP operational state (neighbor session state, timers, transport, global/AFI-SAFI state, prefix counters) alongside Get/Patch/Delete.

### 1.1.2 Configuration and Management Requirements
BGP configurations can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration.

### 1.1.3 Scalability Requirements
The maximum number of BGP neighbors and peer groups depends on platform capabilities and available resources.

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC exposes BGP and local-aggregate configuration through OpenConfig YANG under the network-instance protocol tree. UMF transformers translate REST/gNMI requests into existing CONFIG_DB `BGP_*` and `ROUTE_REDISTRIBUTE` entries; frrcfgd programs FRR bgpd/mgmtd from CONFIG_DB changes.

### 1.2.2 Container
Management Framework container (REST server and gNMI) in *sonic-mgmt-common*.

# 2 Functionality
## 2.1 Target Deployment Use Cases
All northbound clients configure and query BGP using OpenConfig YANG over REST or gNMI.

1. **REST clients** — GET, POST, PUT, PATCH, and DELETE on BGP RESTCONF paths.
2. **gNMI clients** — Capabilities, Get, Set (update/delete), and Subscribe on BGP gNMI paths.

# 3 Design
## 3.1 Overview
This HLD follows [Management Framework.md](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md). The design covers: SONiC feature YANG, OpenConfig modules, UMF translation, CONFIG_DB, FRR programming, mapping tables (Section 4), and unit tests (Section 7).

### 3.1.1 SONiC Feature YANG and CONFIG_DB
SONiC defines the southbound BGP schema in existing CONFIG_DB tables:

| Item | Detail |
|------|--------|
| CONFIG_DB tables | `BGP_GLOBALS`, `BGP_GLOBALS_AF`, `BGP_GLOBALS_AF_NETWORK`, `BGP_GLOBALS_LISTEN_PREFIX`, `BGP_NEIGHBOR`, `BGP_NEIGHBOR_AF`, `BGP_PEER_GROUP`, `BGP_PEER_GROUP_AF`, `BGP_GLOBALS_AF_AGGREGATE_ADDR`, `ROUTE_REDISTRIBUTE` |
| STATE_DB tables | `BGP_GLOBALS_TABLE`, `BGP_GLOBALS_AF_TABLE`, `BGP_NEIGHBOR_AF_TABLE`, `NEIGH_STATE_TABLE` |

OpenConfig clients never write CONFIG_DB directly; UMF transformers populate these tables from OpenConfig payloads.

### 3.1.2 OpenConfig Modules
| Module | Source | Role for BGP |
|--------|--------|--------------|
| [openconfig-network-instance.yang](https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance.yang) | openconfig/public | Protocol container, table-connections, tables |
| [openconfig-bgp.yang](https://github.com/openconfig/public/blob/master/release/models/bgp/openconfig-bgp.yang) | openconfig/public | BGP global, neighbors, peer-groups, AFI-SAFIs |
| [openconfig-bgp-types.yang](https://github.com/openconfig/public/blob/master/release/models/bgp/openconfig-bgp-types.yang) | openconfig/public | BGP identity and type definitions |
| openconfig-network-instance-ext.yang | sonic-mgmt-common | SONiC BGP and local-aggregate extension leaves |
| openconfig-network-instance-annot.yang | sonic-mgmt-common | XPath to CONFIG_DB and operational state bindings |
| openconfig-network-instance-deviation.yang | sonic-mgmt-common | `not-supported` deviations |

### 3.1.3 UMF Translation (REST/gNMI to CONFIG_DB)
OpenConfig SET/GET/SUBSCRIBE requests are handled by translib and the **transformer** common app. Annotation YANG defines xpath-to-DB bindings; BGP transformers perform protocol validation, neighbor/peergroup mapping, and operational state retrieval.

![Management Framework Architecture diagram](images/Mgmt_Frmk_Arch.jpg)

*Figure: Management Framework architecture ([Management Framework.md](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md)).*

#### Table 2: Translation Flow Layers

| Layer | Artifact | Role |
|-------|----------|------|
| **1. SONiC feature YANG** | BGP-related sonic YANG modules | CONFIG_DB `BGP_*` and `ROUTE_REDISTRIBUTE` schema |
| **2. OpenConfig modules** | `openconfig-network-instance.yang`, `openconfig-bgp.yang`, `openconfig-network-instance-ext.yang` | Northbound client model |
| **3. UMF annotations** | `openconfig-network-instance-annot.yang` | XPath → table/field/transformer binding |
| **4. UMF transformers** | BGP transformer | YangToDb / DbToYang / Subscribe for BGP and local aggregates |
| **5. CONFIG_DB** | `BGP_*`, `ROUTE_REDISTRIBUTE` | Runtime configuration store |
| **6. FRR** | `frrcfgd.py` + `bgpd.db.conf.j2` | Programs FRR bgpd/mgmtd |

### 3.1.4 FRR Programming (frrcfgd and Templates)
CONFIG_DB `BGP_*` and `ROUTE_REDISTRIBUTE` changes are consumed by **frrcfgd**, which programs FRR bgpd/mgmtd at runtime. Boot-time configuration is rendered from Jinja2 templates under `templates/bgpd/`.

![FRR Unified Management Framework](images/FRR-BGP-Unified-mgmt-frmwrk.png)

*Figure: Unified FRR management framework ([SONiC Unified FRR Mgmt Interface HLD](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md)).*

Section 4 mapping tables include the corresponding FRR `vtysh` CLI fragment programmed by frrcfgd where applicable.

### 3.1.5 OpenConfig Extensions
SONiC augments base OpenConfig BGP and local-aggregate models using `openconfig-network-instance-ext.yang`.

| Property | Value |
|----------|-------|
| Module | `openconfig-network-instance-ext.yang` |
| Prefix | `oc-network-instance-ext` |
| Namespace | `http://openconfig.net/yang/network-instance/sonic/extension` |

Extension leaf DB and FRR mappings are documented in [Section 4](#4-openconfig-to-sonic-mapping-table) only.

The augment index below lists BGP-related extension nodes in scope (paths only — no DB columns). Config and state leaves are listed once per container; operational-only state leaves are noted.

| OpenConfig YANG Node | Data type | Notes |
|----------------------|-----------|-------|
| **table-connections/table-connection/config** | | |
| metric | uint32 | |
| **table-connections/table-connection/state** | | |
| metric | uint32 | |
| **local-aggregates/aggregate/config** | | |
| summary-only | boolean | |
| as-set | boolean | |
| export-policy | leafref | |
| **local-aggregates/aggregate/state** | | |
| summary-only | boolean | |
| as-set | boolean | |
| export-policy | leafref | |
| **bgp/global/config** | | |
| enable-default-ipv4-unicast-afi | boolean | |
| max-dynamic-neighbor-prefixes | uint16 | |
| disable-ebgp-connected-route-check | boolean | |
| fast-external-failover | boolean | |
| default-local-preference | uint32 | |
| **bgp/global/state** | | |
| enable-default-ipv4-unicast-afi | boolean | |
| max-dynamic-neighbor-prefixes | uint16 | |
| disable-ebgp-connected-route-check | boolean | |
| fast-external-failover | boolean | |
| default-local-preference | uint32 | |
| route-attribute-entry-count | uint32 | Operational only |
| attribute-database-size | uint64 | Operational only |
| as-path-entry-count | uint32 | Operational only |
| as-path-database-size | uint64 | Operational only |
| **bgp/global/graceful-restart/config** | | |
| preserve-fw-state | boolean | |
| disable-end-of-rib-marker | boolean | |
| **bgp/global/use-multiple-paths/ebgp/config** | | |
| as-set | boolean | |
| **bgp/global/route-selection-options/config** | | |
| network-import-check | boolean | |
| compare-confed-as-path | boolean | |
| deterministic-med | boolean | |
| med-confed | boolean | |
| med-missing-as-worst | boolean | |
| **bgp/global/apply-policy/config** | | |
| ebgp-requires-policy | boolean | Augments base `apply-policy` container |
| **bgp/global/logging-options/config** | | |
| log-neighbor-state-changes | boolean | |
| **bgp/global/timers/config** | | |
| hold-time | uint16 | |
| keepalive-interval | uint16 | |
| **bgp/global/bgp-ext-config/config** | | |
| read-quanta | uint8 | |
| write-quanta | uint8 | |
| coalesce-time | uint32 | |
| show-hostname | boolean | |
| shutdown | boolean | |
| subgroup-pkt-queue-max | uint8 | |
| max-delay | uint16 | |
| establish-wait | uint16 | |
| route-map-process-delay | uint16 | |
| **bgp/global/max-med/config** | | |
| max-med-time | uint32 | |
| max-med-val | uint32 | |
| max-med-admin | boolean | |
| max-med-admin-val | uint32 | |
| **bgp/global/route-reflector/config** | | |
| route-reflector-cluster-id | oc-bgp-types:rr-cluster-id-type | |
| allow-out-policy | boolean | |
| client-to-client-reflection | boolean | |
| **bgp/global/graceful-shutdown/config** | | |
| enabled | boolean | |
| **bgp/global/afi-safis/afi-safi/config** | | |
| import-policy | leafref | List |
| local-route-distance | uint8 | |
| external-route-distance | uint8 | |
| internal-route-distance | uint8 | |
| **bgp/global/afi-safis/afi-safi/state** | | |
| table-version | uint32 | Operational only |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/config** | | |
| advertise-all-vni | boolean | |
| advertise-ipv4-unicast | boolean | |
| advertise-ipv6-unicast | boolean | |
| advertise-svi-ip | boolean | |
| advertise-default-gateway | boolean | |
| disable-ethernet-segment-l3-nexthop-gateway | boolean | |
| route-distinguisher | oc-ni-types:route-distinguisher | |
| auto-route-target | enumeration | |
| flooding | enumeration | |
| default-originate-ipv4 | boolean | |
| default-originate-ipv6 | boolean | |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/duplicate-address-detection/config** | | |
| enabled | boolean | |
| max-moves | uint16 | |
| detection-time | uint16 | |
| freeze | union | |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/route-target/config** | | |
| import-route-target | string | List |
| export-route-target | string | List |
| **bgp/global/afi-safis/afi-safi/import-sources/import-source/config** | | |
| source-network-instance | leafref | |
| import-policy | leafref | |
| **bgp/global/afi-safis/afi-safi/route-flap-damping/config** | | |
| enabled | boolean | |
| half-life | uint8 | |
| reuse-threshold | uint16 | |
| suppress-threshold | uint16 | |
| max-suppress | uint8 | |
| **bgp/global/afi-safis/afi-safi/networks/network/config** | | |
| prefix | inet:ip-prefix | |
| backdoor | boolean | |
| **bgp/global/afi-safis/afi-safi/networks/network/apply-policy/config** | | |
| export-policy | leafref | |
| **bgp/neighbors/neighbor/config** | | |
| disable-ebgp-connected-route-check | boolean | |
| extended-next-hop-encoding | boolean | |
| solo-peer | boolean | |
| ttl-security-hops | uint8 | |
| dynamic-capability-negotiation | boolean | |
| disable-capability-negotiation | boolean | |
| override-capability | boolean | |
| strict-capability-match | boolean | |
| shutdown-message | string | |
| **bgp/neighbors/neighbor/state** | | |
| received-prefixes-count | uint32 | Operational only |
| advertised-capability | string | Operational only |
| received-capability | string | Operational only |
| last-flap-timestamp | string | Operational only |
| remote-router-id | oc-yang:dotted-quad | Operational only |
| **bgp/neighbors/neighbor/state/messages/sent** | | |
| KEEPALIVE | uint64 | Operational only |
| ROUTE-REFRESH | uint64 | Operational only |
| **bgp/neighbors/neighbor/state/messages/received** | | |
| KEEPALIVE | uint64 | Operational only |
| ROUTE-REFRESH | uint64 | Operational only |
| **bgp/neighbors/neighbor/transport/state** | | |
| local-ip | inet:ip-address | Operational only |
| **bgp/neighbors/neighbor/ebgp-multihop/config** | | |
| enforce-multihop | boolean | |
| **bgp/neighbors/neighbor/as-path-options/config** | | |
| enforce-first-as | boolean | |
| local-as-no-prepend | boolean | |
| local-as-replace-as | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/config** | | |
| soft-reconfiguration-inbound | boolean | |
| replace-peer-as | boolean | |
| route-server-client | boolean | |
| outbound-route-filtering-capability | enumeration | |
| weight | uint16 | |
| route-reflector-client | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/state** | | |
| flushed | uint32 | Operational only; under `prefixes` |
| table-version | uint64 | Operational only |
| peer-table-version | uint32 | Operational only |
| accepted-path-count | uint32 | Operational only |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/add-paths/config** | | |
| send-best-path-per-as | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/apply-policy/config** | | |
| import-as-path-set | leafref | Augments base `apply-policy` |
| export-as-path-set | leafref | |
| import-prefix-set | leafref | |
| export-prefix-set | leafref | |
| default-originate-policy | leafref | |
| unsuppress-map-policy | leafref | |
| next-hop-self | boolean | |
| next-hop-self-force | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv4-unicast/prefix-limit/config** | | |
| restart-time | uint16 | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv6-unicast/prefix-limit/config** | | |
| restart-time | uint16 | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/allow-own-as/config** | | |
| enabled | boolean | |
| as-count | uint8 | |
| origin | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/remove-private-as/config** | | |
| enabled | boolean | |
| all | boolean | |
| replace-private-as | boolean | |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/attribute-transparency/config** | | |
| preserve-as-path-enabled | boolean | |
| preserve-med-enabled | boolean | |
| preserve-next-hop-enabled | boolean | |
| **bgp/neighbors/neighbor/enable-bfd/config** | | |
| check-control-plane-failure | boolean | |
| strict-mode | boolean | |
| **bgp/peer-groups/peer-group/config** | | |
| enabled | boolean | |
| neighbor-port | oc-inet:port-number | |
| disable-ebgp-connected-route-check | boolean | |
| extended-next-hop-encoding | boolean | |
| solo-peer | boolean | |
| ttl-security-hops | uint8 | |
| dynamic-capability-negotiation | boolean | |
| disable-capability-negotiation | boolean | |
| override-capability | boolean | |
| strict-capability-match | boolean | |
| shutdown-message | string | |
| **bgp/peer-groups/peer-group/ebgp-multihop/config** | | |
| enforce-multihop | boolean | |
| **bgp/peer-groups/peer-group/as-path-options/config** | | |
| enforce-first-as | boolean | |
| local-as-no-prepend | boolean | |
| local-as-replace-as | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/config** | | |
| soft-reconfiguration-inbound | boolean | |
| replace-peer-as | boolean | |
| route-server-client | boolean | |
| outbound-route-filtering-capability | enumeration | |
| weight | uint16 | |
| route-reflector-client | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/add-paths/config** | | |
| send-best-path-per-as | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy/config** | | |
| import-as-path-set | leafref | Augments base `apply-policy` |
| export-as-path-set | leafref | |
| import-prefix-set | leafref | |
| export-prefix-set | leafref | |
| default-originate-policy | leafref | |
| unsuppress-map-policy | leafref | |
| next-hop-self | boolean | |
| next-hop-self-force | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv4-unicast/prefix-limit/config** | | |
| restart-time | uint16 | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv6-unicast/prefix-limit/config** | | |
| restart-time | uint16 | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/allow-own-as/config** | | |
| enabled | boolean | |
| as-count | uint8 | |
| origin | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/remove-private-as/config** | | |
| enabled | boolean | |
| all | boolean | |
| replace-private-as | boolean | |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/attribute-transparency/config** | | |
| preserve-as-path-enabled | boolean | |
| preserve-med-enabled | boolean | |
| preserve-next-hop-enabled | boolean | |
| **bgp/peer-groups/peer-group/enable-bfd/config** | | |
| check-control-plane-failure | boolean | |
| strict-mode | boolean | |

### 3.1.6 Mapping Table and Unit Tests
- **OpenConfig → SONiC mapping:** [Section 4](#4-openconfig-to-sonic-mapping-table).
- **REST/gNMI examples:** [Section 5](#5-user-interface).
- **Unit tests:** [Section 7](#7-unit-test-cases).

## 3.2 DB Changes
OpenConfig BGP uses existing CONFIG_DB and STATE_DB tables. No new tables are added.

### 3.2.1 CONFIG DB
- BGP_GLOBALS
- BGP_GLOBALS_AF
- BGP_GLOBALS_AF_NETWORK
- BGP_GLOBALS_LISTEN_PREFIX
- BGP_NEIGHBOR
- BGP_NEIGHBOR_AF
- BGP_PEER_GROUP
- BGP_PEER_GROUP_AF
- BGP_GLOBALS_AF_AGGREGATE_ADDR
- ROUTE_REDISTRIBUTE

### 3.2.2 APP DB
There are no APP DB changes for BGP configuration.

### 3.2.3 STATE DB
- BGP_GLOBALS_AF_TABLE (BGP global AFI-SAFI operational data)
- BGP_GLOBALS_TABLE (BGP global operational data)
- BGP_NEIGHBOR_AF_TABLE (neighbor AFI-SAFI prefix counters)
- NEIGH_STATE_TABLE (BGP neighbor session state, timers, capabilities)

### 3.2.4 ASIC DB
There are no ASIC DB changes for BGP.

### 3.2.5 COUNTER DB
There are no COUNTER DB changes for BGP.


# 4 OpenConfig to SONiC Mapping Table

**Key notation:**
- **OpenConfig YANG Node** — Parent container or list paths appear in **bold** on their own row; child leaves below use the leaf name only (relative to the parent path above). Extension augments omit the `oc-network-instance-ext:` prefix in paths and leaf names.
- **Extension** — `Yes` on extension leaves; blank on base OpenConfig leaves. Extension definitions are in [§3.1.5](#315-openconfig-extensions).
- **DB Name** — Redis database (`CONFIG_DB`, `STATE_DB`, or `—` for derived values).
- **Table:Field** — SONiC table and field in `TABLE:field` form; table-only or `Derived` when the value is computed or encoded in the Redis key.
- `Derived` — value computed by a transformer or encoded in the Redis key.
- **FRR CLI (vtysh)** — inferred command fragment programmed by **frrcfgd** from CONFIG_DB (see `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` and `templates/bgpd/*.j2`). Shown relative to `configure terminal` → `router bgp <asn> [vrf <vrf>]` and, where noted, inside `address-family` context. Placeholders: `<asn>`, `<vrf>`, `<nbr>`, `<pg>`, `<prefix>`, `<name>`, `<sec>`, `<n>`, `<id>`, `<half-life>`, `<reuse-threshold>`, `<suppress-threshold>`, `<max-suppress>`. Optional FRR keywords use `[...]`; mutually exclusive value choices use `/` between forms in the FRR CLI column. `—` means no FRR config CLI (operational/read-only or derived).
- Redis key formats are noted in the Notes column where applicable.

## 4.1 BGP Global
| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **bgp/global/config** |  |  |  |  |  |
| as |  | CONFIG_DB | BGP_GLOBALS:local_asn | `router bgp <asn> [vrf <vrf>]` | Via transformer |
| router-id |  | CONFIG_DB | BGP_GLOBALS:router_id | `bgp router-id <id>` |  |
| default-local-preference | Yes | CONFIG_DB | BGP_GLOBALS:default_local_preference | `bgp default local-preference <n>` |  |
| disable-ebgp-connected-route-check | Yes | CONFIG_DB | BGP_GLOBALS:disable_ebgp_connected_rt_check | `bgp disable-ebgp-connected-route-check` |  |
| enable-default-ipv4-unicast-afi | Yes | CONFIG_DB | BGP_GLOBALS:default_ipv4_unicast | `bgp default ipv4-unicast` |  |
| fast-external-failover | Yes | CONFIG_DB | BGP_GLOBALS:fast_external_failover | `bgp fast-external-failover` |  |
| max-dynamic-neighbor-prefixes | Yes | CONFIG_DB | BGP_GLOBALS:max_dynamic_neighbors | `bgp listen limit <n>` |  |
| **bgp/global/state** |  |  |  |  |  |
| as-path-database-size | Yes | STATE_DB | BGP_GLOBALS_TABLE:as_path_database_size | — | Via transformer |
| as-path-entry-count | Yes | STATE_DB | BGP_GLOBALS_TABLE:as_path_entry_count | — | Via transformer |
| attribute-database-size | Yes | STATE_DB | BGP_GLOBALS_TABLE:attribute_database_size | — | Via transformer |
| route-attribute-entry-count | Yes | STATE_DB | BGP_GLOBALS_TABLE:route_attribute_entry_count | — | Via transformer |
| **bgp/global/confederation/config** |  |  |  |  |  |
| identifier |  | CONFIG_DB | BGP_GLOBALS:confed_id | `bgp confederation identifier <id>` |  |
| member-as |  | CONFIG_DB | BGP_GLOBALS:confed_peers | `bgp confederation peers <as-list>` |  |
| **bgp/global/graceful-restart/config** |  |  |  |  |  |
| enabled |  | CONFIG_DB | BGP_GLOBALS:graceful_restart_enable | `bgp graceful-restart` |  |
| restart-time |  | CONFIG_DB | BGP_GLOBALS:gr_restart_time | `bgp graceful-restart restart-time <sec>` |  |
| stale-routes-time |  | CONFIG_DB | BGP_GLOBALS:gr_stale_routes_time | `bgp graceful-restart stalepath-time <sec>` |  |
| preserve-fw-state | Yes | CONFIG_DB | BGP_GLOBALS:gr_preserve_fw_state | `bgp graceful-restart preserve-fw-state` |  |
| disable-end-of-rib-marker | Yes | CONFIG_DB | BGP_GLOBALS:gr_disable_end_of_rib_marker | `bgp graceful-restart disable-eor` | Direct annotation mapping |
| **bgp/global/graceful-restart/state** |  |  |  |  |  |
| disable-end-of-rib-marker | Yes | CONFIG_DB | BGP_GLOBALS:gr_disable_end_of_rib_marker | — | GET symmetry with config |
| **bgp/global/use-multiple-paths/ebgp/config** |  |  |  |  |  |
| allow-multiple-as |  | CONFIG_DB | BGP_GLOBALS:load_balance_mp_relax | `bgp bestpath as-path multipath-relax [as-set or no-as-set]` |  |
| as-set | Yes | CONFIG_DB | BGP_GLOBALS:as_path_mp_as_set | `bgp bestpath as-path multipath-relax as-set` |  |
| **bgp/global/route-selection-options/config** |  |  |  |  |  |
| always-compare-med |  | CONFIG_DB | BGP_GLOBALS:always_compare_med | `bgp always-compare-med` |  |
| ignore-as-path-length |  | CONFIG_DB | BGP_GLOBALS:ignore_as_path_length | `bgp bestpath as-path ignore` |  |
| external-compare-router-id |  | CONFIG_DB | BGP_GLOBALS:external_compare_router_id | `bgp bestpath compare-routerid` |  |
| compare-confed-as-path | Yes | CONFIG_DB | BGP_GLOBALS:compare_confed_as_path | `bgp bestpath as-path confed` |  |
| deterministic-med | Yes | CONFIG_DB | BGP_GLOBALS:deterministic_med | `bgp deterministic-med` |  |
| med-confed | Yes | CONFIG_DB | BGP_GLOBALS:med_confed | `bgp bestpath med confed` |  |
| med-missing-as-worst | Yes | CONFIG_DB | BGP_GLOBALS:med_missing_as_worst | `bgp bestpath med missing-as-worst` |  |
| network-import-check | Yes | CONFIG_DB | BGP_GLOBALS:network_import_check | `bgp network import-check` |  |
| **bgp/global/apply-policy/config** | Yes |  |  |  |  |
| ebgp-requires-policy | Yes | CONFIG_DB | BGP_GLOBALS:ebgp_requires_policy | `bgp ebgp-requires-policy` |  |
| **bgp/global/apply-policy/state** | Yes |  |  |  |  |
| ebgp-requires-policy | Yes | CONFIG_DB | BGP_GLOBALS:ebgp_requires_policy | — | GET symmetry with config |
| **bgp/global/logging-options/config** | Yes |  |  |  |  |
| log-neighbor-state-changes | Yes | CONFIG_DB | BGP_GLOBALS:log_nbr_state_changes | `bgp log-neighbor-changes` |  |
| **bgp/global/timers/config** | Yes |  |  |  |  |
| hold-time | Yes | CONFIG_DB | BGP_GLOBALS:holdtime | `timers bgp <keepalive> <holdtime>` | Via transformer |
| keepalive-interval | Yes | CONFIG_DB | BGP_GLOBALS:keepalive | `timers bgp <keepalive> <holdtime>` | Via transformer |
| **bgp/global/bgp-ext-config/config** | Yes |  |  |  |  |
| coalesce-time | Yes | CONFIG_DB | BGP_GLOBALS:coalesce_time | `coalesce-time <n>` |  |
| establish-wait | Yes | CONFIG_DB | BGP_GLOBALS:establish_wait | `update-delay <max_delay> <establish_wait>` |  |
| max-delay | Yes | CONFIG_DB | BGP_GLOBALS:max_delay | `update-delay <max_delay> [<establish_wait>]` |  |
| read-quanta | Yes | CONFIG_DB | BGP_GLOBALS:read_quanta | `read-quanta <n>` |  |
| route-map-process-delay | Yes | CONFIG_DB | BGP_GLOBALS:route_map_process_delay | `bgp route-map delay-timer <sec>` |  |
| show-hostname | Yes | CONFIG_DB | BGP_GLOBALS:default_show_hostname | `bgp default show-hostname` |  |
| shutdown | Yes | CONFIG_DB | BGP_GLOBALS:default_shutdown | `bgp default shutdown` |  |
| subgroup-pkt-queue-max | Yes | CONFIG_DB | BGP_GLOBALS:default_subgroup_pkt_queue_max | `bgp default subgroup-pkt-queue-max <n>` |  |
| write-quanta | Yes | CONFIG_DB | BGP_GLOBALS:write_quanta | `write-quanta <n>` |  |
| **bgp/global/max-med/config** | Yes |  |  |  |  |
| max-med-admin | Yes | CONFIG_DB | BGP_GLOBALS:max_med_admin | `bgp max-med administrative [<val>]` |  |
| max-med-admin-val | Yes | CONFIG_DB | BGP_GLOBALS:max_med_admin_val | `bgp max-med administrative <val>` |  |
| max-med-time | Yes | CONFIG_DB | BGP_GLOBALS:max_med_time | `bgp max-med on-startup [<time>] [<val>]` |  |
| max-med-val | Yes | CONFIG_DB | BGP_GLOBALS:max_med_val | `bgp max-med on-startup <time> <val>` |  |
| **bgp/global/route-reflector/config** | Yes |  |  |  |  |
| allow-out-policy | Yes | CONFIG_DB | BGP_GLOBALS:rr_allow_out_policy | `bgp route-reflector allow-outbound-policy` |  |
| client-to-client-reflection | Yes | CONFIG_DB | BGP_GLOBALS:rr_clnt_to_clnt_reflection | `bgp client-to-client reflection` |  |
| route-reflector-cluster-id | Yes | CONFIG_DB | BGP_GLOBALS:rr_cluster_id | `bgp cluster-id <id>` | Via transformer |
| **bgp/global/graceful-shutdown/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_GLOBALS:graceful_shutdown | `bgp graceful-shutdown` |  |

## 4.2 BGP Global AFI-SAFIs
| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **bgp/global/afi-safis** |  |  |  |  |  |
| afi-safi |  | CONFIG_DB | BGP_GLOBALS_AF | — | Context / key in Redis; key `bgp_af_key_xfmr`; Key: vrf |
| **bgp/global/afi-safis/afi-safi/config** |  |  |  |  |  |
| external-route-distance | Yes | CONFIG_DB | BGP_GLOBALS_AF:ebgp_route_distance | `distance bgp <ebgp> <ibgp> <local>` |  |
| import-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_download_filter | `table-map <name>` | Via transformer |
| internal-route-distance | Yes | CONFIG_DB | BGP_GLOBALS_AF:ibgp_route_distance | `distance bgp <ebgp> <ibgp> <local>` |  |
| local-route-distance | Yes | CONFIG_DB | BGP_GLOBALS_AF:local_route_distance | `distance bgp <ebgp> <ibgp> <local>` |  |
| **bgp/global/afi-safis/afi-safi/state** |  |  |  |  |  |
| table-version | Yes | STATE_DB | BGP_GLOBALS_AF_TABLE:tableVersion | — | Via transformer |
| **bgp/global/afi-safis/afi-safi/use-multiple-paths/ebgp/config** |  |  |  |  |  |
| maximum-paths |  | CONFIG_DB | BGP_GLOBALS_AF:max_ebgp_paths | `maximum-paths <n>` |  |
| **bgp/global/afi-safis/afi-safi/use-multiple-paths/ibgp/config** |  |  |  |  |  |
| maximum-paths |  | CONFIG_DB | BGP_GLOBALS_AF:max_ibgp_paths | `maximum-paths ibgp <n> [equal-cluster-length]` |  |
| **bgp/global/afi-safis/afi-safi/import-sources** | Yes |  |  |  |  |
| import-source | Yes | CONFIG_DB | BGP_GLOBALS_AF | — | Subtree bgp_af_import_sources_xfmr; key bgp_af_import_source_key_xfmr; list collapses onto parent row (vrf and afi_safi, pipe-separated; same key as BGP_GLOBALS_AF) |
| **import-sources/import-source/config** | Yes |  |  |  |  |
| source-network-instance | Yes | CONFIG_DB | BGP_GLOBALS_AF:import_vrf | `import vrf <vrf>` | Via subtree `bgp_af_import_sources_xfmr`; list key `source-network-instance` |
| import-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF:import_vrf_route_map | `import vrf route-map <name>` | Via subtree `bgp_af_import_sources_xfmr`; DELETE on import-sources container clears fields without deleting the AF row |
| **import-sources/import-source/state** | Yes |  |  |  |  |
| source-network-instance | Yes | CONFIG_DB | BGP_GLOBALS_AF:import_vrf | — | GET symmetry with config; via `DbToYang_bgp_af_import_sources_xfmr` |
| import-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF:import_vrf_route_map | — | GET symmetry with config |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/config** | Yes |  |  |  |  |
| advertise-all-vni | Yes | CONFIG_DB | BGP_GLOBALS_AF:advertise-all-vni | `advertise-all-vni` | Via transformer |
| advertise-default-gateway | Yes | CONFIG_DB | BGP_GLOBALS_AF:advertise-default-gw | `advertise-default-gw` |  |
| advertise-ipv4-unicast | Yes | CONFIG_DB | BGP_GLOBALS_AF:advertise-ipv4-unicast | `advertise ipv4 unicast` |  |
| advertise-ipv6-unicast | Yes | CONFIG_DB | BGP_GLOBALS_AF:advertise-ipv6-unicast | `advertise ipv6 unicast` |  |
| advertise-svi-ip | Yes | CONFIG_DB | BGP_GLOBALS_AF:advertise-svi-ip | `advertise-svi-ip` |  |
| auto-route-target | Yes | CONFIG_DB | BGP_GLOBALS_AF:autort | `autort <mode>` | Via transformer |
| default-originate-ipv4 | Yes | CONFIG_DB | BGP_GLOBALS_AF:default-originate-ipv4 | `default-originate ipv4` |  |
| default-originate-ipv6 | Yes | CONFIG_DB | BGP_GLOBALS_AF:default-originate-ipv6 | `default-originate ipv6` |  |
| flooding | Yes | CONFIG_DB | BGP_GLOBALS_AF:flooding | `flooding <mode>` | Via transformer |
| route-distinguisher | Yes | CONFIG_DB | BGP_GLOBALS_AF:evpn_rd | `rd <rd>` |  |
| disable-ethernet-segment-l3-nexthop-gateway | Yes | CONFIG_DB | BGP_GLOBALS_AF:use_es_l3nhg | `use-es-l3nhg` | Via transformer; boolean inverted vs CONFIG_DB `use_es_l3nhg`; l2vpn_evpn AFI only |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/state** | Yes |  |  |  |  |
| disable-ethernet-segment-l3-nexthop-gateway | Yes | CONFIG_DB | BGP_GLOBALS_AF:use_es_l3nhg | — | GET symmetry with config via `bgp_af_disable_es_l3nhg_xfmr` |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/duplicate-address-detection/config** | Yes |  |  |  |  |
| detection-time | Yes | CONFIG_DB | BGP_GLOBALS_AF:dad-time | `dup-addr-detection max-moves <n> time <sec>` |  |
| enabled | Yes | CONFIG_DB | BGP_GLOBALS_AF:dad-enabled | `dup-addr-detection` |  |
| freeze | Yes | CONFIG_DB | BGP_GLOBALS_AF:dad-freeze | `dup-addr-detection freeze <action>` | Via transformer |
| max-moves | Yes | CONFIG_DB | BGP_GLOBALS_AF:dad-max-moves | `dup-addr-detection max-moves <n> time <sec>` |  |
| **bgp/global/afi-safis/afi-safi/l2vpn-evpn/route-target/config** | Yes |  |  |  |  |
| export-route-target | Yes | CONFIG_DB | BGP_GLOBALS_AF:export-rts | `route-target export <rt>` |  |
| import-route-target | Yes | CONFIG_DB | BGP_GLOBALS_AF:import-rts | `route-target import <rt>` |  |
| **bgp/global/afi-safis/afi-safi/networks** | Yes |  |  |  |  |
| network | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK | — | Context / key in Redis; table `bgp_afi_safi_network_tbl_xfmr`; key `bgp_afi_safi_network_key_xfmr`; Key: vrf |
| **bgp/global/afi-safis/afi-safi/networks/network/config** | Yes |  |  |  |  |
| prefix | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK:ip_prefix | `network <prefix> <route-map or backdoor>` |  |
| backdoor | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK:backdoor | `network <prefix> backdoor` | Direct annotation mapping |
| **bgp/global/afi-safis/afi-safi/networks/network/apply-policy/config** | Yes |  |  |  |  |
| export-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK:policy | `network <prefix> <route-map>` | Direct annotation mapping |
| **bgp/global/afi-safis/afi-safi/networks/network/state** | Yes |  |  |  |  |
| backdoor | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK:backdoor | — | GET symmetry with config |
| **networks/network/apply-policy/state** | Yes |  |  |  |  |
| export-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF_NETWORK:policy | — | GET symmetry with config |
| **bgp/global/afi-safis/afi-safi/route-flap-damping/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_flap_dampen | `bgp dampening [<half-life> <reuse-threshold> <suppress-threshold> <max-suppress>]` |  |
| half-life | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_flap_dampen_half_life | `bgp dampening <half-life> <reuse-threshold> <suppress-threshold> <max-suppress>` |  |
| max-suppress | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_flap_dampen_max_suppress | `bgp dampening <half-life> <reuse-threshold> <suppress-threshold> <max-suppress>` |  |
| reuse-threshold | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_flap_dampen_reuse_threshold | `bgp dampening <half-life> <reuse-threshold> <suppress-threshold> <max-suppress>` |  |
| suppress-threshold | Yes | CONFIG_DB | BGP_GLOBALS_AF:route_flap_dampen_suppress_threshold | `bgp dampening <half-life> <reuse-threshold> <suppress-threshold> <max-suppress>` |  |

## 4.3 BGP Dynamic Neighbor Prefixes
| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **bgp/global/dynamic-neighbor-prefixes** |  | | ||  |
| dynamic-neighbor-prefix | | CONFIG_DB | BGP_GLOBALS_LISTEN_PREFIX | — | key `bgp_global_dynamic_neighbor_prefixes_key_xfmr`; Key: vrf  |
| **bgp/global/dynamic-neighbor-prefixes/dynamic-neighbor-prefix/config** |  | | ||  |
| peer-group | | CONFIG_DB | BGP_GLOBALS_LISTEN_PREFIX:peer_group | `bgp listen range <prefix> peer-group <name>` |   |
| prefix | | CONFIG_DB | BGP_GLOBALS_LISTEN_PREFIX:ip_prefix | `bgp listen range <prefix> peer-group <name>` |   |


## 4.4 BGP Neighbors
| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **bgp/neighbors** |  |  |  |  |  |
| neighbor |  | CONFIG_DB | BGP_NEIGHBOR | — | key `bgp_neighbor_key_xfmr`; path `bgp_neighbor_path_xfmr`; Key: vrf |
| **bgp/neighbors/neighbor/config** |  |  |  |  |  |
| auth-password |  | CONFIG_DB | BGP_NEIGHBOR:auth_password | `neighbor <nbr> password <pwd>` | Via transformer |
| description |  | CONFIG_DB | BGP_NEIGHBOR:name | `neighbor <nbr> description <text>` |  |
| enabled |  | CONFIG_DB | BGP_NEIGHBOR:admin_status | `neighbor <nbr> shutdown` | Via transformer |
| local-as |  | CONFIG_DB | BGP_NEIGHBOR:local_asn | `neighbor <nbr> local-as <asn> <no-prepend> <replace-as>` |  |
| peer-as |  | CONFIG_DB | BGP_NEIGHBOR:asn | `neighbor <nbr> remote-as <asn or internal or external>` |  |
| peer-group |  | CONFIG_DB | BGP_NEIGHBOR:peer_group_name | `neighbor <nbr> peer-group <name>` | Via transformer |
| peer-type |  | CONFIG_DB | BGP_NEIGHBOR:peer_type | `neighbor <nbr> remote-as <asn or internal or external>` | Via transformer |
| neighbor-port |  | CONFIG_DB | BGP_NEIGHBOR:peer_port | `neighbor <nbr> port <n>` |  |
| disable-ebgp-connected-route-check | Yes | CONFIG_DB | BGP_NEIGHBOR:disable_ebgp_connected_route_check | `neighbor <nbr> disable-connected-check` | global uses `BGP_GLOBALS:disable_ebgp_connected_rt_check` (different field name, same FRR feature) |
| extended-next-hop-encoding | Yes | CONFIG_DB | BGP_NEIGHBOR:capability_ext_nexthop | `neighbor <nbr> capability extended-nexthop` |  |
| solo-peer | Yes | CONFIG_DB | BGP_NEIGHBOR:solo_peer | `neighbor <nbr> solo` |  |
| ttl-security-hops | Yes | CONFIG_DB | BGP_NEIGHBOR:ttl_security_hops | `neighbor <nbr> ttl-security hops <n>` |  |
| dynamic-capability-negotiation | Yes | CONFIG_DB | BGP_NEIGHBOR:capability_dynamic | `neighbor <nbr> capability dynamic` |  |
| disable-capability-negotiation | Yes | CONFIG_DB | BGP_NEIGHBOR:dont_negotiate_capability | `neighbor <nbr> dont-capability-negotiate` |  |
| override-capability | Yes | CONFIG_DB | BGP_NEIGHBOR:override_capability | `neighbor <nbr> override-capability` |  |
| strict-capability-match | Yes | CONFIG_DB | BGP_NEIGHBOR:strict_capability_match | `neighbor <nbr> strict-capability-match` |  |
| shutdown-message | Yes | CONFIG_DB | BGP_NEIGHBOR:shutdown_message | `neighbor <nbr> shutdown message <text>` |  |
| **bgp/neighbors/neighbor/state** |  |  |  |  |  |
| description |  | STATE_DB | NEIGH_STATE_TABLE:description | — |  |
| last-established |  | STATE_DB | NEIGH_STATE_TABLE:uptime | — | Via transformer |
| local-as |  | STATE_DB | NEIGH_STATE_TABLE:localAsn | — | Via transformer |
| advertised-capability | Yes | STATE_DB | NEIGH_STATE_TABLE:advCapabilities | — | Via transformer |
| last-flap-timestamp | Yes | STATE_DB | NEIGH_STATE_TABLE:lastFlapTimeStamp | — | Via transformer |
| received-capability | Yes | STATE_DB | NEIGH_STATE_TABLE:rcvCapabilities | — | Via transformer |
| remote-router-id | Yes | STATE_DB | NEIGH_STATE_TABLE:remoteRouterId | — | Via transformer |
| peer-as |  | STATE_DB | NEIGH_STATE_TABLE:remoteAs | — | Via transformer |
| peer-type |  | STATE_DB | NEIGH_STATE_TABLE:peerType | — | Via transformer; config `peer-type` is also mapped (see `bgp/neighbors/neighbor/config`) |
| session-state |  | STATE_DB | NEIGH_STATE_TABLE:state | — | Via transformer |
| received-prefixes-count | Yes | STATE_DB | NEIGH_STATE_TABLE:rcvdPfx | — | Via transformer |
| enabled |  | CONFIG_DB | BGP_NEIGHBOR:admin_status | — | Via transformer; GET symmetry with config |
| neighbor-port |  | CONFIG_DB | BGP_NEIGHBOR:peer_port | — | GET symmetry with config |
| **bgp/neighbors/neighbor/state/messages/received** | Yes |  |  |  |  |
| KEEPALIVE | Yes | STATE_DB | NEIGH_STATE_TABLE:keepalivesRecv | — | Via transformer |
| ROUTE-REFRESH | Yes | STATE_DB | NEIGH_STATE_TABLE:routeRefreshRecv | — | Via transformer |
| **bgp/neighbors/neighbor/state/messages/sent** | Yes |  |  |  |  |
| KEEPALIVE | Yes | STATE_DB | NEIGH_STATE_TABLE:keepalivesSent | — | Via transformer |
| ROUTE-REFRESH | Yes | STATE_DB | NEIGH_STATE_TABLE:routeRefreshSent | — | Via transformer |
| **bgp/neighbors/neighbor/timers/config** |  |  |  |  |  |
| connect-retry |  | CONFIG_DB | BGP_NEIGHBOR:conn_retry | `neighbor <nbr> timers connect <sec>` |  |
| hold-time |  | CONFIG_DB | BGP_NEIGHBOR:holdtime | `neighbor <nbr> timers <keepalive> <holdtime>` | Via transformer |
| keepalive-interval |  | CONFIG_DB | BGP_NEIGHBOR:keepalive | `neighbor <nbr> timers <keepalive> <holdtime>` | Via transformer |
| minimum-advertisement-interval |  | CONFIG_DB | BGP_NEIGHBOR:min_adv_interval | `neighbor <nbr> advertisement-interval <sec>` |  |
| **bgp/neighbors/neighbor/timers/state** |  |  |  |  |  |
| hold-time |  | STATE_DB | NEIGH_STATE_TABLE:holdTime | — | Via transformer |
| keepalive-interval |  | STATE_DB | NEIGH_STATE_TABLE:keepAlive | — | Via transformer |
| **bgp/neighbors/neighbor/transport/config** |  |  |  |  |  |
| local-address |  | CONFIG_DB | BGP_NEIGHBOR:local_addr | `neighbor <nbr> update-source <addr-or-if>` |  |
| passive-mode |  | CONFIG_DB | BGP_NEIGHBOR:passive_mode | `neighbor <nbr> passive` |  |
| tcp-mss |  | CONFIG_DB | BGP_NEIGHBOR:tcp_mss | `neighbor <nbr> tcp-mss <n>` |  |
| **bgp/neighbors/neighbor/transport/state** |  |  |  |  |  |
| local-address |  | STATE_DB | NEIGH_STATE_TABLE:updateSource | — | Via transformer |
| local-port |  | STATE_DB | NEIGH_STATE_TABLE:local_port | — | Via transformer |
| local-ip | Yes | STATE_DB | NEIGH_STATE_TABLE:local_address | — | Via transformer |
| remote-port |  | STATE_DB | NEIGH_STATE_TABLE:remote_port | — | Via transformer |
| **bgp/neighbors/neighbor/afi-safis** |  |  |  |  |  |
| afi-safi |  | CONFIG_DB | BGP_NEIGHBOR_AF | — | key `bgp_neighbor_afi_safi_key_xfmr`; path `bgp_neighbor_afi_safi_path_xfmr`; Key: vrf |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/config** |  |  |  |  |  |
| afi-safi-name |  | CONFIG_DB | BGP_NEIGHBOR_AF:afi_safi | `address-family context` |  |
| enabled |  | CONFIG_DB | BGP_NEIGHBOR_AF:admin_status | `neighbor <nbr> activate` | Via transformer |
| send-community-type |  | CONFIG_DB | BGP_NEIGHBOR_AF:send_community | `neighbor <nbr> send-community <community-type>` | Via transformer; FRR values: standard, extended, large, both, none; only the first leaf-list element is used |
| soft-reconfiguration-inbound | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:soft_reconfiguration_in | `neighbor <nbr> soft-reconfiguration inbound` |  |
| replace-peer-as | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:as_override | `neighbor <nbr> as-override` |  |
| route-reflector-client | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:rrclient | `neighbor <nbr> route-reflector-client` |  |
| route-server-client | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:route_server_client | `neighbor <nbr> route-server-client` |  |
| outbound-route-filtering-capability | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:cap_orf | `neighbor <nbr> capability orf prefix-list` | Via transformer |
| weight | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:weight | `neighbor <nbr> weight <n>` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/state** |  |  |  |  |  |
| accepted-path-count | Yes | STATE_DB | NEIGH_STATE_TABLE:acceptedPaths | — | Via transformer; read from NEIGH_STATE_TABLE (per-neighbor, 2-part key); same value returned for every AFI-SAFI until bgpmon adds per-AF data to BGP_NEIGHBOR_AF_TABLE |
| peer-table-version | Yes | STATE_DB | NEIGH_STATE_TABLE:peerTableVersion | — | Via transformer; read from NEIGH_STATE_TABLE (per-neighbor, 2-part key); same value returned for every AFI-SAFI until bgpmon adds per-AF data to BGP_NEIGHBOR_AF_TABLE |
| table-version | Yes | STATE_DB | NEIGH_STATE_TABLE:localTableVersion | — | Via transformer; read from NEIGH_STATE_TABLE (per-neighbor, 2-part key); same value returned for every AFI-SAFI until bgpmon adds per-AF data to BGP_NEIGHBOR_AF_TABLE |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/state/prefixes** |  |  |  |  |  |
| installed |  | STATE_DB | BGP_NEIGHBOR_AF_TABLE:installedPrefixCounter | — | Via transformer |
| flushed | Yes | STATE_DB | BGP_NEIGHBOR_AF_TABLE:flushedPrefixCounter | — | Via transformer |
| received |  | STATE_DB | BGP_NEIGHBOR_AF_TABLE:acceptedPrefixCounter | — | Via transformer; OC "received" = post-policy Adj-RIB-In count (FRR `acceptedPrefixCounter`), not raw receive count |
| received-pre-policy |  | STATE_DB | BGP_NEIGHBOR_AF_TABLE:receivedPrePolicyPrefixCounter | — | Via transformer |
| sent |  | STATE_DB | BGP_NEIGHBOR_AF_TABLE:sentPrefixCounter | — | Via transformer |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/apply-policy/config** |  |  |  |  |  |
| export-policy |  | CONFIG_DB | BGP_NEIGHBOR_AF:route_map_out | `neighbor <nbr> route-map <name> out` | Via transformer |
| import-policy |  | CONFIG_DB | BGP_NEIGHBOR_AF:route_map_in | `neighbor <nbr> route-map <name> in` | Via transformer |
| next-hop-self | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:nhself | `neighbor <nbr> next-hop-self [force]` |  |
| next-hop-self-force | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:nexthop_self_force | `neighbor <nbr> next-hop-self force` |  |
| default-originate-policy | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:default_rmap | `neighbor <nbr> default-originate route-map <name>` |  |
| unsuppress-map-policy | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:unsuppress_map_name | `neighbor <nbr> unsuppress-map <name>` |  |
| import-as-path-set | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:filter_list_in | `neighbor <nbr> filter-list <name> in` |  |
| export-as-path-set | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:filter_list_out | `neighbor <nbr> filter-list <name> out` |  |
| import-prefix-set | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:prefix_list_in | `neighbor <nbr> prefix-list <name> in` |  |
| export-prefix-set | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:prefix_list_out | `neighbor <nbr> prefix-list <name> out` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/add-paths/config** |  |  |  |  |  |
| send |  | CONFIG_DB | BGP_NEIGHBOR_AF:tx_add_paths | `neighbor <nbr> addpath-tx-all-paths / addpath-tx-bestpath-per-AS` | Via transformer |
| send-max |  | CONFIG_DB | BGP_NEIGHBOR_AF:tx_add_best_path_count | `neighbor <nbr> addpath-tx-bestpath-per-AS` | Via transformer |
| send-best-path-per-as |  | CONFIG_DB | BGP_NEIGHBOR_AF:tx_add_paths | `neighbor <nbr> addpath-tx-bestpath-per-AS` | Via transformer |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/allow-own-as/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:allow_as_in | `neighbor <nbr> allowas-in` |  |
| as-count | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:allow_as_count | `neighbor <nbr> allowas-in <count>` |  |
| origin | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:allow_as_origin | `neighbor <nbr> allowas-in origin` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/remove-private-as/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:remove_private_as_enabled | `neighbor <nbr> remove-private-AS` |  |
| all | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:remove_private_as_all | `neighbor <nbr> remove-private-AS all` |  |
| replace-private-as | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:replace_private_as | `neighbor <nbr> remove-private-AS replace-AS` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/attribute-transparency/config** | Yes |  |  |  |  |
| preserve-as-path-enabled | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:unchanged_as_path | `neighbor <nbr> attribute-unchanged as-path` |  |
| preserve-med-enabled | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:unchanged_med | `neighbor <nbr> attribute-unchanged med` |  |
| preserve-next-hop-enabled | Yes | CONFIG_DB | BGP_NEIGHBOR_AF:unchanged_nexthop | `neighbor <nbr> attribute-unchanged next-hop` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv4-unicast/config** |  |  |  |  |  |
| send-default-route |  | CONFIG_DB | BGP_NEIGHBOR_AF:send_default_route | `neighbor <nbr> default-originate` | IPv4 unicast AFI-SAFI only |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv4-unicast/prefix-limit/config** |  |  |  |  |  |
| max-prefixes |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_limit | `neighbor <nbr> maximum-prefix <n>` |  |
| prevent-teardown |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_warning_only | `neighbor <nbr> maximum-prefix <n> warning-only` |  |
| warning-threshold-pct |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_warning_threshold | `neighbor <nbr> maximum-prefix <n> <pct>` |  |
| restart-time |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_restart_interval | `neighbor <nbr> maximum-prefix <n> restart <sec>` |  |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv6-unicast/config** |  |  |  |  |  |
| send-default-route |  | CONFIG_DB | BGP_NEIGHBOR_AF:send_default_route | `neighbor <nbr> default-originate` | IPv6 unicast AFI-SAFI only |
| **bgp/neighbors/neighbor/afi-safis/afi-safi/ipv6-unicast/prefix-limit/config** |  |  |  |  |  |
| max-prefixes |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_limit | `neighbor <nbr> maximum-prefix <n>` |  |
| prevent-teardown |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_warning_only | `neighbor <nbr> maximum-prefix <n> warning-only` |  |
| warning-threshold-pct |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_warning_threshold | `neighbor <nbr> maximum-prefix <n> <pct>` |  |
| restart-time |  | CONFIG_DB | BGP_NEIGHBOR_AF:max_prefix_restart_interval | `neighbor <nbr> maximum-prefix <n> restart <sec>` |  |
| **bgp/neighbors/neighbor/ebgp-multihop/config** |  |  |  |  |  |
| enabled |  | CONFIG_DB | BGP_NEIGHBOR:ebgp_multihop | `neighbor <nbr> ebgp-multihop [<ttl>]` |  |
| multihop-ttl |  | CONFIG_DB | BGP_NEIGHBOR:ebgp_multihop_ttl | `neighbor <nbr> ebgp-multihop <ttl>` |  |
| enforce-multihop | Yes | CONFIG_DB | BGP_NEIGHBOR:enforce_multihop | `neighbor <nbr> enforce-multihop` |  |
| **bgp/neighbors/neighbor/enable-bfd/config** |  |  |  |  |  |
| desired-minimum-tx-interval |  | CONFIG_DB | BGP_NEIGHBOR:desired_minimum_tx_interval | `neighbor <nbr> bfd <mult> <rx> <tx>` |  |
| detection-multiplier |  | CONFIG_DB | BGP_NEIGHBOR:detection_multiplier | `neighbor <nbr> bfd <mult> <rx> <tx>` |  |
| enabled |  | CONFIG_DB | BGP_NEIGHBOR:bfd | `neighbor <nbr> bfd` |  |
| required-minimum-receive |  | CONFIG_DB | BGP_NEIGHBOR:required_minimum_receive | `neighbor <nbr> bfd <mult> <rx> <tx>` |  |
| check-control-plane-failure | Yes | CONFIG_DB | BGP_NEIGHBOR:bfd_check_ctrl_plane_failure | `neighbor <nbr> bfd check-control-plane-failure` | requires BFD enabled |
| strict-mode | Yes | CONFIG_DB | BGP_NEIGHBOR:bfd_strict_mode | `neighbor <nbr> bfd strict` | requires BFD enabled |
| **bgp/neighbors/neighbor/as-path-options/config** | Yes |  |  |  |  |
| enforce-first-as | Yes | CONFIG_DB | BGP_NEIGHBOR:enforce_first_as | `neighbor <nbr> enforce-first-as` |  |
| local-as-no-prepend | Yes | CONFIG_DB | BGP_NEIGHBOR:local_as_no_prepend | `neighbor <nbr> local-as no-prepend` |  |
| local-as-replace-as | Yes | CONFIG_DB | BGP_NEIGHBOR:local_as_replace_as | `neighbor <nbr> local-as replace-as` |  |

## 4.5 BGP Peer Groups
| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **bgp/peer-groups** |  |  |  |  |  |
| peer-group |  | CONFIG_DB | BGP_PEER_GROUP | — | key `bgp_peergroup_key_xfmr`; Key: vrf |
| **bgp/peer-groups/peer-group/config** |  |  |  |  |  |
| peer-group-name |  | CONFIG_DB | BGP_PEER_GROUP:peer_group_name | `neighbor <pg> peer-group <name>` |  |
| peer-as |  | CONFIG_DB | BGP_PEER_GROUP:asn | `neighbor <pg> remote-as <asn or internal or external>` |  |
| local-as |  | CONFIG_DB | BGP_PEER_GROUP:local_asn | `neighbor <pg> local-as <asn> <no-prepend> <replace-as>` |  |
| peer-type |  | CONFIG_DB | BGP_PEER_GROUP:peer_type | `neighbor <pg> remote-as <asn or internal or external>` | Via transformer |
| auth-password |  | CONFIG_DB | BGP_PEER_GROUP:auth_password | `neighbor <pg> password <pwd>` | Via transformer |
| description |  | CONFIG_DB | BGP_PEER_GROUP:name | `neighbor <pg> description <text>` |  |
| disable-capability-negotiation | Yes | CONFIG_DB | BGP_PEER_GROUP:dont_negotiate_capability | `neighbor <pg> dont-capability-negotiate` |  |
| disable-ebgp-connected-route-check | Yes | CONFIG_DB | BGP_PEER_GROUP:disable_ebgp_connected_route_check | `neighbor <pg> disable-connected-check` |  |
| dynamic-capability-negotiation | Yes | CONFIG_DB | BGP_PEER_GROUP:capability_dynamic | `neighbor <pg> capability dynamic` |  |
| enabled | Yes | CONFIG_DB | BGP_PEER_GROUP:admin_status | `neighbor <pg> shutdown` | Via transformer |
| extended-next-hop-encoding | Yes | CONFIG_DB | BGP_PEER_GROUP:capability_ext_nexthop | `neighbor <pg> capability extended-nexthop` |  |
| neighbor-port | Yes | CONFIG_DB | BGP_PEER_GROUP:peer_port | `neighbor <pg> port <n>` | see neighbor `neighbor-port` (§4.4) |
| override-capability | Yes | CONFIG_DB | BGP_PEER_GROUP:override_capability | `neighbor <pg> override-capability` |  |
| shutdown-message | Yes | CONFIG_DB | BGP_PEER_GROUP:shutdown_message | `neighbor <pg> shutdown message <text>` |  |
| solo-peer | Yes | CONFIG_DB | BGP_PEER_GROUP:solo_peer | `neighbor <pg> solo` |  |
| strict-capability-match | Yes | CONFIG_DB | BGP_PEER_GROUP:strict_capability_match | `neighbor <pg> strict-capability-match` |  |
| ttl-security-hops | Yes | CONFIG_DB | BGP_PEER_GROUP:ttl_security_hops | `neighbor <pg> ttl-security hops <n>` |  |
| **bgp/peer-groups/peer-group/timers/config** |  |  |  |  |  |
| connect-retry |  | CONFIG_DB | BGP_PEER_GROUP:conn_retry | `neighbor <pg> timers connect <sec>` |  |
| hold-time |  | CONFIG_DB | BGP_PEER_GROUP:holdtime | `neighbor <pg> timers <keepalive> <holdtime>` | Via transformer |
| keepalive-interval |  | CONFIG_DB | BGP_PEER_GROUP:keepalive | `neighbor <pg> timers <keepalive> <holdtime>` | Via transformer |
| minimum-advertisement-interval |  | CONFIG_DB | BGP_PEER_GROUP:min_adv_interval | `neighbor <pg> advertisement-interval <sec>` |  |
| **bgp/peer-groups/peer-group/transport/config** |  |  |  |  |  |
| local-address |  | CONFIG_DB | BGP_PEER_GROUP:local_addr | `neighbor <pg> update-source <addr-or-if>` |  |
| passive-mode |  | CONFIG_DB | BGP_PEER_GROUP:passive_mode | `neighbor <pg> passive` |  |
| tcp-mss |  | CONFIG_DB | BGP_PEER_GROUP:tcp_mss | `neighbor <pg> tcp-mss <n>` |  |
| **bgp/peer-groups/peer-group/graceful-restart/config** |  |  |  |  |  |
| enabled |  | CONFIG_DB | BGP_PEER_GROUP:graceful_restart_enable | `neighbor <pg> graceful-restart` |  |
| **bgp/peer-groups/peer-group/ebgp-multihop/config** |  |  |  |  |  |
| enabled |  | CONFIG_DB | BGP_PEER_GROUP:ebgp_multihop | `neighbor <pg> ebgp-multihop [<ttl>]` |  |
| multihop-ttl |  | CONFIG_DB | BGP_PEER_GROUP:ebgp_multihop_ttl | `neighbor <pg> ebgp-multihop <ttl>` |  |
| enforce-multihop | Yes | CONFIG_DB | BGP_PEER_GROUP:enforce_multihop | `neighbor <pg> enforce-multihop` |  |
| **bgp/peer-groups/peer-group/enable-bfd/config** |  |  |  |  |  |
| desired-minimum-tx-interval |  | CONFIG_DB | BGP_PEER_GROUP:desired_minimum_tx_interval | `neighbor <pg> bfd <mult> <rx> <tx>` |  |
| detection-multiplier |  | CONFIG_DB | BGP_PEER_GROUP:detection_multiplier | `neighbor <pg> bfd <mult> <rx> <tx>` |  |
| enabled |  | CONFIG_DB | BGP_PEER_GROUP:bfd | `neighbor <pg> bfd` |  |
| check-control-plane-failure | Yes | CONFIG_DB | BGP_PEER_GROUP:bfd_check_ctrl_plane_failure | `neighbor <pg> bfd check-control-plane-failure` |  |
| strict-mode | Yes | CONFIG_DB | BGP_PEER_GROUP:bfd_strict_mode | `neighbor <pg> bfd strict` |  |
| required-minimum-receive |  | CONFIG_DB | BGP_PEER_GROUP:required_minimum_receive | `neighbor <pg> bfd <mult> <rx> <tx>` |  |
| **bgp/peer-groups/peer-group/as-path-options/config** | Yes |  |  |  |  |
| enforce-first-as | Yes | CONFIG_DB | BGP_PEER_GROUP:enforce_first_as | `neighbor <pg> enforce-first-as` |  |
| local-as-no-prepend | Yes | CONFIG_DB | BGP_PEER_GROUP:local_as_no_prepend | `neighbor <pg> local-as <asn> no-prepend` |  |
| local-as-replace-as | Yes | CONFIG_DB | BGP_PEER_GROUP:local_as_replace_as | `neighbor <pg> local-as <asn> replace-as` |  |
| **bgp/peer-groups/peer-group/afi-safis** |  |  |  |  |  |
| afi-safi |  | CONFIG_DB | BGP_PEER_GROUP_AF | — | key `bgp_peergroup_afi_safi_key_xfmr`; Key: vrf |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/add-paths/config** |  |  |  |  |  |
| send |  | CONFIG_DB | BGP_PEER_GROUP_AF:tx_add_paths | `neighbor <pg> addpath-tx-all-paths / addpath-tx-bestpath-per-AS` | Via transformer |
| send-max |  | CONFIG_DB | BGP_PEER_GROUP_AF:tx_add_best_path_count | `neighbor <pg> addpath-tx-bestpath-per-AS` | Via transformer |
| send-best-path-per-as |  | CONFIG_DB | BGP_PEER_GROUP_AF:tx_add_paths | `neighbor <pg> addpath-tx-bestpath-per-AS` | Via transformer |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/apply-policy/config** |  |  |  |  |  |
| export-policy |  | CONFIG_DB | BGP_PEER_GROUP_AF:route_map_out | `neighbor <pg> route-map <name> out` | Via transformer |
| import-policy |  | CONFIG_DB | BGP_PEER_GROUP_AF:route_map_in | `neighbor <pg> route-map <name> in` | Via transformer |
| next-hop-self | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:nhself | `neighbor <pg> next-hop-self [force]` |  |
| next-hop-self-force | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:nexthop_self_force | `neighbor <pg> next-hop-self force` |  |
| default-originate-policy | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:default_rmap | `neighbor <pg> default-originate route-map <name>` |  |
| unsuppress-map-policy | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:unsuppress_map_name | `neighbor <pg> unsuppress-map <name>` |  |
| import-as-path-set | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:filter_list_in | `neighbor <pg> filter-list <name> in` |  |
| export-as-path-set | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:filter_list_out | `neighbor <pg> filter-list <name> out` |  |
| import-prefix-set | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:prefix_list_in | `neighbor <pg> prefix-list <name> in` |  |
| export-prefix-set | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:prefix_list_out | `neighbor <pg> prefix-list <name> out` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/config** |  |  |  |  |  |
| afi-safi-name |  | CONFIG_DB | BGP_PEER_GROUP_AF:afi_safi | `address-family context` |  |
| enabled |  | CONFIG_DB | BGP_PEER_GROUP_AF:admin_status | `neighbor <pg> activate` | Via transformer |
| send-community-type |  | CONFIG_DB | BGP_PEER_GROUP_AF:send_community | `neighbor <pg> send-community <community-type>` | Via transformer |
| soft-reconfiguration-inbound |  | CONFIG_DB | BGP_PEER_GROUP_AF:soft_reconfiguration_in | `neighbor <pg> soft-reconfiguration inbound` |  |
| replace-peer-as | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:as_override | `neighbor <pg> as-override` |  |
| route-reflector-client | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:rrclient | `neighbor <pg> route-reflector-client` |  |
| route-server-client | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:route_server_client | `neighbor <pg> route-server-client` |  |
| outbound-route-filtering-capability | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:cap_orf | `neighbor <pg> capability orf prefix-list` | Via transformer |
| weight | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:weight | `neighbor <pg> weight <n>` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/allow-own-as/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:allow_as_in | `neighbor <pg> allowas-in` |  |
| as-count | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:allow_as_count | `neighbor <pg> allowas-in <count>` |  |
| origin | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:allow_as_origin | `neighbor <pg> allowas-in origin` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/remove-private-as/config** | Yes |  |  |  |  |
| enabled | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:remove_private_as_enabled | `neighbor <pg> remove-private-AS` |  |
| all | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:remove_private_as_all | `neighbor <pg> remove-private-AS all` |  |
| replace-private-as | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:replace_private_as | `neighbor <pg> remove-private-AS replace-AS` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/attribute-transparency/config** | Yes |  |  |  |  |
| preserve-as-path-enabled | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:unchanged_as_path | `neighbor <pg> attribute-unchanged as-path` |  |
| preserve-med-enabled | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:unchanged_med | `neighbor <pg> attribute-unchanged med` |  |
| preserve-next-hop-enabled | Yes | CONFIG_DB | BGP_PEER_GROUP_AF:unchanged_nexthop | `neighbor <pg> attribute-unchanged next-hop` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv4-unicast/config** |  |  |  |  |  |
| send-default-route |  | CONFIG_DB | BGP_PEER_GROUP_AF:send_default_route | `neighbor <pg> default-originate` | IPv4 unicast AFI-SAFI only |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv4-unicast/prefix-limit/config** |  |  |  |  |  |
| max-prefixes |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_limit | `neighbor <pg> maximum-prefix <n>` |  |
| prevent-teardown |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_warning_only | `neighbor <pg> maximum-prefix <n> warning-only` |  |
| warning-threshold-pct |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_warning_threshold | `neighbor <pg> maximum-prefix <n> <pct>` |  |
| restart-time |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_restart_interval | `neighbor <pg> maximum-prefix <n> restart <sec>` |  |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv6-unicast/config** |  |  |  |  |  |
| send-default-route |  | CONFIG_DB | BGP_PEER_GROUP_AF:send_default_route | `neighbor <pg> default-originate` | IPv6 unicast AFI-SAFI only |
| **bgp/peer-groups/peer-group/afi-safis/afi-safi/ipv6-unicast/prefix-limit/config** |  |  |  |  |  |
| max-prefixes |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_limit | `neighbor <pg> maximum-prefix <n>` |  |
| prevent-teardown |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_warning_only | `neighbor <pg> maximum-prefix <n> warning-only` |  |
| warning-threshold-pct |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_warning_threshold | `neighbor <pg> maximum-prefix <n> <pct>` |  |
| restart-time |  | CONFIG_DB | BGP_PEER_GROUP_AF:max_prefix_restart_interval | `neighbor <pg> maximum-prefix <n> restart <sec>` |  |

**Neighbor and peergroup AFI-SAFI limitation:** The `l2vpn-evpn` container under neighbor/peergroup `afi-safis/afi-safi` is **not supported** (`not-supported` in `openconfig-network-instance-deviation.yang`). Configure L2VPN EVPN under global `bgp/global/afi-safis/afi-safi[l2vpn-evpn]` (§4.2).

## 4.6 Local Aggregates

Local aggregates use a separate `protocols/protocol` entry (`identifier=LOCAL_AGGREGATE`, `name=bgp`). `BGP_GLOBALS` must exist for the VRF before aggregates are accepted (BGP global prerequisite validation).

OpenConfig path: `/network-instances/network-instance/protocols/protocol[identifier=LOCAL_AGGREGATE][name=bgp]/local-aggregates/...`

| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **local-aggregates** |  | | ||  |
| aggregate | | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR | — | table `local_aggregate_tbl_xfmr`; key `local_aggregate_key_xfmr`; Key: vrf  |
| **local-aggregates/aggregate/config** | Yes | | ||  |
| prefix | | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:ip_prefix | `aggregate-address <prefix> [as-set] [summary-only] [route-map <name>]` | Via transformer; key component  |
| summary-only | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:summary_only | `aggregate-address <prefix> [summary-only]` |   |
| as-set | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:as_set | `aggregate-address <prefix> [as-set]` |   |
| export-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:policy | `aggregate-address <prefix> route-map <name>` |   |
| **local-aggregates/aggregate/state** | Yes | | ||  |
| prefix | | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:ip_prefix | — | Via transformer  |
| summary-only | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:summary_only | — |   |
| as-set | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:as_set | — |   |
| export-policy | Yes | CONFIG_DB | BGP_GLOBALS_AF_AGGREGATE_ADDR:policy | — |   |

## 4.7 Table Connections and Tables

Route redistribution is configured under `table-connections/table-connection` and mapped to CONFIG_DB `ROUTE_REDISTRIBUTE`. Operational routing tables are exposed under `tables/table` (GET-only). Implemented via table-connection transformer.

**Supported `table-connection` combinations:**

| src-protocol | dst-protocol | SET/PATCH/DELETE | CONFIG_DB key format |
|--------------|--------------|------------------|----------------------|
| `DIRECTLY_CONNECTED` | `BGP` | Supported | `{vrf}|connected|bgp|{ipv4 or ipv6}` |
| `STATIC` | `BGP` | Supported | `{vrf}|static|bgp|{ipv4 or ipv6}` |
| `LOCAL_AGGREGATE` | `BGP` | GET only | Derived from `BGP_GLOBALS_AF`; configure aggregates under `local-aggregates` |

| OpenConfig YANG Node | Extension | DB Name | Table:Field | `FRR CLI (vtysh)` | Notes |
|----------------------|-----------|---------|-------------|-----------------|-------|
| **table-connections** | | | ||  |
| table-connection | | CONFIG_DB | ROUTE_REDISTRIBUTE | `redistribute <src_protocol> [route-map <name>]` | table network_instance_table_connection_tbl_xfmr; key network_instance_table_connection_key_xfmr; Redis key components vrf, src_protocol, dst_protocol, addr_family (pipe-delimited); BGP_GLOBALS must exist for the VRF |
| **table-connections/table-connection/config** | | | ||  |
| import-policy | | CONFIG_DB | ROUTE_REDISTRIBUTE:route_map | `redistribute <src_protocol> route-map <name>` | Via transformer; only **one** route-map allowed (leaf-list max 1)  |
| metric | Yes | CONFIG_DB | ROUTE_REDISTRIBUTE:metric | `redistribute <src_protocol> metric <n>` |  |
| **table-connections/table-connection/state** | | | ||  |
| import-policy | | CONFIG_DB | ROUTE_REDISTRIBUTE:route_map | — | GET symmetry with config |
| metric | Yes | CONFIG_DB | ROUTE_REDISTRIBUTE:metric | — | GET symmetry with config |
| **tables/table** | | | ||  |
| table | | Derived | key component | — | table `network_instance_table_tbl_xfmr`; GET-only; UPDATE/REPLACE/DELETE not supported on `tables/table`  |

**Cascade delete behavior:** Deleting the BGP protocol container or an entire VRF removes associated `ROUTE_REDISTRIBUTE` entries where `dst_protocol=bgp` for that VRF (cascade delete on BGP protocol or VRF removal).

# 5 User Interface

## 5.1 Data Models
| Model | Source | Purpose |
|-------|--------|---------|
| [openconfig-network-instance.yang](https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance.yang) | openconfig/public | Protocol container, table-connections |
| [openconfig-bgp.yang](https://github.com/openconfig/public/blob/master/release/models/bgp/openconfig-bgp.yang) | openconfig/public | BGP configuration and state |
| openconfig-network-instance-ext.yang | sonic-mgmt-common | SONiC BGP extension leaves |


## 5.2 REST API Support
### 5.2.1 GET
Supported at all BGP container and leaf levels.

Sample GET request:
```
curl -X GET -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp" -H "accept: application/yang-data+json"
```

Sample GET output:
```json
{
  "openconfig-network-instance:protocol": [
    {
      "identifier": "BGP",
      "name": "bgp",
      "bgp": {
        "global": {
          "config": { "as": 65100, "router-id": "10.10.10.1" },
          "state": { "as": 65100, "router-id": "10.10.10.1" }
        }
      }
    }
  ]
}
```

### 5.2.2 PATCH
Sample PATCH request for BGP global AS number:
```
curl -X PATCH -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/global/config/as" \
  -H "Content-Type: application/yang-data+json" \
  -d '{"openconfig-network-instance:as": 65100}'
```

Sample PATCH request for BGP neighbor:
```
curl -X PATCH -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/neighbors/neighbor=10.0.0.1" \
  -H "Content-Type: application/yang-data+json" \
  -d '{
    "openconfig-network-instance:neighbor": [
      {
        "neighbor-address": "10.0.0.1",
        "config": {
          "neighbor-address": "10.0.0.1",
          "peer-as": 65200,
          "description": "BGP Neighbor"
        }
      }
    ]
  }'
```

### 5.2.3 DELETE
Sample DELETE request for BGP neighbor:
```
curl -X DELETE -k "https://<device>/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/neighbors/neighbor=10.0.0.1"
```

## 5.3 gNMI Support
GET, SET (update/delete), and Subscribe are supported on in-scope BGP paths. Subscribe applies to operational `state` containers (neighbor session state, timers, transport, global/AFI-SAFI state, prefix counters). Config leaves use GET/SET only.

### 5.3.1 GET
Sample gNMI GET request:
```
gnmic -a <device>:<port> --insecure --target OC-YANG get --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/config"
```

### 5.3.2 SET
Sample gNMI SET request:
```
gnmic -a <device>:<port> --insecure --target OC-YANG set --update "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/config:@bgp_global.json"
```

### 5.3.3 DELETE
Sample gNMI DELETE request:
```
gnmic -a <device>:<port> --insecure --target OC-YANG set --delete "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=10.0.0.1]"
```

### 5.3.4 SUBSCRIBE
Supported for BGP operational state paths. Use `--target OC-YANG`. Wildcard neighbor keys (`neighbor-address=*`) are supported for telemetry subscriptions.

Sample ON_CHANGE subscription on BGP neighbor session state (controller-agent `BGP_Session_State` on-change telemetry):

```
gnmic -a <device>:<port> --insecure --target OC-YANG subscribe \
  --stream-mode on_change \
  --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/state/session-state"
```

Sample SAMPLE stream subscription on BGP neighbor operational state (controller-agent periodic `BGP` dial-out telemetry):

```
gnmic -a <device>:<port> --insecure --target OC-YANG subscribe \
  --path "/openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/state" \
  --mode stream
```

Sample ON_CHANGE notification when a neighbor transitions to ESTABLISHED:

```
{
  "source": "<device>:<port>",
  "subscription-name": "default-<timestamp>",
  "timestamp": 1758089943763134718,
  "prefix": "openconfig-network-instance:network-instances/network-instance[name=default]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=10.0.0.1]/state",
  "target": "OC-YANG",
  "updates": [
    {
      "Path": "session-state",
      "values": {
        "session-state": "ESTABLISHED"
      }
    }
  ]
}
```

# 6 Error Handling
Invalid configurations will report an error. Examples include:
- Invalid AS numbers
- Invalid IP addresses or prefixes
- Missing required fields (e.g., AS number before neighbor config)
- Conflicting configurations
- Invalid AFI-SAFI name
- Invalid peer-group reference in neighbor


Supported AFI-SAFI names in this release: `IPV4_UNICAST`, `IPV6_UNICAST`, and `L2VPN_EVPN` only.

BGP timer coupling (global, neighbor, and peergroup): hold-time must be ≥ 3× keepalive-interval; hold-time and keepalive must be configured together; DELETE of either leaf alone (without deleting the entire timers container) is rejected.

# 7 Unit Test Cases

## 7.1 Functional Test Cases
1. Global AFI-SAFI import-sources: POST/PATCH/GET/DELETE; DELETE on import-sources container clears `import_vrf`/`import_vrf_route_map` without removing `BGP_GLOBALS_AF` row.
2. Global AFI-SAFI network: CRUD for prefix, backdoor, and export-policy.
3. Neighbor extension config leaves: solo-peer, ttl-security-hops, capability negotiation leaves, shutdown-message, disable-ebgp-connected-route-check, extended-next-hop-encoding.
4. Neighbor as-path-options: enforce-first-as, local-as-no-prepend, local-as-replace-as.
5. Neighbor ebgp-multihop `enforce-multihop` and BFD extensions (`check-control-plane-failure`, `strict-mode`).
6. Neighbor standard `neighbor-port` and config `peer-type`.
7. Neighbor AFI-SAFI `send-community-type`: standard, extended, large, both, none (first leaf-list value only).
8. Neighbor operational state: session-state, prefix counters (received, received-pre-policy, installed, sent, flushed), message counters (KEEPALIVE, ROUTE-REFRESH).

## 7.2 Negative Test Cases
1. Import-source with `source-network-instance` equal to parent VRF → rejected (YANG must).
2. Hold-time less than 3× keepalive-interval → rejected (neighbor and peergroup).
3. Hold-time or keepalive configured without the other → rejected.
4. DELETE of hold-time or keepalive alone (without deleting entire timers container) → rejected.
5. More than one import- or export-policy on neighbor/peergroup AFI-SAFI → rejected.
6. Change peer-group on an existing neighbor → rejected ("Cannot change the peer-group. Deconfigure first").
7. Neighbor, dynamic-neighbor, or local-aggregate config without global AS (`BGP_GLOBALS`) for the VRF → rejected; unsupported AFI-SAFI name (e.g. `IPV6_LABELED_UNICAST`) → rejected.
