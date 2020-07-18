# Sonic PIM-SSM (IPv4) Management-framework Support

Implement PIM-SSM (IPv4) configuration via REST/CLI/gNMI in SONiC Mgmt-framework

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#Revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#1.1-requirements)
      * [1.1.1 Configuration and Management Requirements](#1.1.1-configuration-and-management-requirements)
      * [1.1.2 Scalability Requirements](#1.1.2-scalability-requirements)
    * [1.2 Design Overview](#1.2-design-overview)
       * [1.2.1 Basic Approach](#1.2.1-basic-approach)
       * [1.2.2 Container](#1.2.2-container)
  * [2 Functionality](#2-functionality)
    * [2.1 Target Deployment Use Case](#2.1-target-deployment-use-case)
    * [2.2 Functional Description](#2.2-functional-description)
  * [3 Design](#3-design)
    * [3.1 Overview](#3.1-overview)
    * [3.2 DB Changes](#3.2-db-changes)
      * [3.2.1 CONFIG DB](#3.2.1-config-db)
      * [3.2.2 APP DB](3.2.2-app-db)
      * [3.2.3 STATE DB](3.2.3-state-db)
      * [3.2.4 ASIC DB](3.2.4-asic-db)
      * [3.2.5 COUNTER DB](3.2.5-counter-db)
    * [3.3 User Interface](3.3-user-interface)
      * [3.3.1 Data Models](3.3.1-data-models)
      * [3.3.2 CLI](3.3.2-cli)
        * [3.3.2.1 Configuration Commands](3.3.2.1-configuration-commands)
          * [3.3.2.1.1 Global Configuration Commands](3.3.2.1.1-global-configuration-commands)
          * [3.3.2.1.2 Interface specific Configuration Commands](3.3.2.1.2-interface-specific-Configuration-Commands)
        * [3.3.2.2 Show Commands](3.3.2.2-show-commands)
          * [3.3.2.2.1 Global Multicast Show commands](3.3.2.2.1-global-multicast-show-commands)
          * [3.3.2.2.2 PIM-SSM (IPv4) Show commands](3.3.2.2.2-pim-ssm-ipv4-show-commands)
        * [3.3.2.3 show running-config & show configuration](3.3.2.3-show-running-config-&-show-configuration)
          * [3.3.2.3.1 show running-config](3.3.2.3.1-show-running-config)
          * [3.3.2.3.2 show configuration](3.3.2.3.2-show-configuration)
        * [3.3.2.4 Debug Commands](3.3.2.3-debug-commands)
          * [3.3.2.4.1 Global Multicast Clear commands](3.3.2.4.1-global-multicast-clear-commands)
          * [3.3.2.4.2 PIM-SSM (IPv4) Clear commands](3.3.2.4.2-pim-ssm-ipv4-clear-commands)
        * [3.3.2.5 IS-CLI Compliance](3.3.2.5-iscli-compliance)
      * [3.3.3 REST API Support](3.3.3-rest-api-support)
      * [3.3.4 gNMI Support](3.3.4-gnmi-support)
  * [4 Flow Diagrams](4-flow-diagrams)
  * [5 Error Handling](5-error-handling)
  * [6 Serviceability and Debug](6-serviceability-and-debug)
  * [7 Warm Boot Support](7-warm-boot-support)
  * [8 Unit Test](8-unit-test)



# Revision
| Rev |     Date    |       Author                  | Change Description                |
|-----|-------------|-------------------------------|-----------------------------------|
| 0.1 | 06/16/2020  |  Rathnasabapathy Velautharaj  | Initial version                   |

# About this Manual
This document provides general information about configuring PIM Source Specific Multicast (IPv4) via Management REST/CLI/gNMI in Sonic.

# Scope
This document describes the changes required in Sonic Mgmt-framework to support configuration for PIM Source Specific Multicast (IPv4) via REST/CLI/gNMI. It covers details about the CLI commands added in Mgmt-framework and the corresponding openconfig & Sonic yang model supported for configuration.

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**  | ***Meaning***                                                     |
|-----------|-------------------------------------------------------------------|
| PIM-SSM   | PIM - Source Specific Multicast                                   |
| IGMP      | Internet Group Management Protocol                                |
| IGMPv3    | IGMP version 3                                                    |
| SPT       | Shortest Path Tree                                                |
| RPF       | Reverse Path Forwarding                                           |
| (S,G)     | (Source address, Group address)                                   |
| VRF       | Virtual Router Forwarding                                         |
| LHR       | Last Hop Router (Router directly connected to the Host/Receiver   |
| FHR       | First Hop Router (Router directly connected to the Source/Sender  |
| FRR       | Free Range Routing                                                |
| OIF/OIL   | Outgoing Interface List                                           |
| IIF       | Incoming interface                                                |
| SSM Range | 232.0.0.0/8                                                       |

# 1 Feature Overview

PIM-SSM (IPv4) support is already available in Sonic, by configuring FRR directly through VTYSH. The corresponding changes to push FRR's PIM configurations & IP multicast routes to SAI is present as well.

Here this section explains the changes required in Sonic for PIM-SSM (IPv4) Mgmt-framework support through REST/CLI/gNMI using Openconfig & Sonic yang.

## 1.1 Requirements
### 1.1.1 Configuration and Management Requirements
1. Support to configure PIM-SSM (IPv4) & display information using KLISH CLI commands
2. Support to configure PIM-SSM (IPv4) & GET through Openconfig yang via REST & gNMI
3. Support IPv4 multicast forwarding/routing on Port based, VLAN based and LAG based routing interfaces
4. Support IPv4 multicast forwarding/routing in a VRF
5. Support PIM neighbor reachability tracking using BFD
6. Show running-config support
7. Config save & restore support

### 1.1.2 Scalability Requirements
The following are the scalability requirements for this feature:
1. Maximum number of PIM neighbors supported is 64.
2. Maximum number of multicast route entries supported is 8K.

These scalability numbers are exactly same as current support in Sonic through configurations directly via FRR(VTYSH). It's been validated through configurations via Mgmt-framework.

## 1.2 Design Overview
### 1.2.1 Basic Approach
Existing PIM-SSM (IPv4) including VRF support available in Sonic through FRR has been extended to provide management support via management-framework to configure via CLI, REST & gNMI using Openconfig yang. New tables are introduced for configuration via Sonic-yang in config-db. These new tables will be monitored by bgpcfgd daemon running in BGP-container and these configurations will be sent to FRR via vtysh shell.

### 1.2.2 Container
* **management-framework** :
  * Transformer Changes to convert the Openconfig yang configurations to Sonic-yang (Config-DB). This will enable the config support via REST/gNMI
  * CLI XML, python-actioner & Jinja-template changes to support CLI-style configurations and relevant show/clear commands. CLI will internally do REST calls via openconfig yang. For “clear” and a few “show” commands, it does REST calls through Sonic-yang (RPC).
* **bgp** :
  * bgpcfgd service inside this container will be enhanced to monitor the changes in PIM-SSM config-DB tables to push the management-framework configurations to FRR via VTYSH shell. 'pimd' running inside FRR will take care of applying these configurations.



# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure PIM-SSM (IPv4) with VRF support via gNMI, REST and CLI interfaces.

## 2.2 Functional Description
Provide CLI, gNMI and REST support via the Management Framework for PIM-SSM (IPv4) with VRF related handling.

# 3 Design

## 3.1 Overview

The design described in this section provides enhancements to the management framework backend code and transformer methods to add support for PIM-SSM (IPv4) with VRF related handling.

## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow the user to perform PIM-SSM (IPv4) with VRF related configuration changes to CONFIG DB.

PIM-SSM requires a few global configurations & interface-specific configurations. Hence, these two tables are introduced for that purpose.
* Global configurations are keyed by "vrf-name address-family".
* Interface-specific configurations are keyed using "vrf-name address-family interface".

Address-family specifiers are introduced here to enable extending PIM-support to IPv6 in the future with fewer changes in the config DB. For now, only IPv4 specific configurations are supported.

```JSON
PIM Global Configuration Table:
==============================

Key                       : PIM_GLOBALS|vrf-name|address-family

vrf-Name                  : 1-15 characters ; VRF name
address-family            : enum {ipv4}

join-prune-interval       : Join prune interval in seconds. Range (60-600 seconds)
keep-alive-timer          : Keep alive timer in seconds. Range (31-60000 seconds)
ssm-ranges                : Configure Source-Specific-Multicast group range using IP Prefix-list
ecmp-enabled              : To enable PIM ECMP (true/false)
ecmp-rebalance-enabled    : To enable PIM ECMP rebalance (true/false). It can be enabled/disabled only when ECMP is enabled
```

```JSON
PIM Interface-Specific Configuration Table:
==========================================

Key                       : PIM_INTERFACE|vrf-name|address-family|interface

vrf-Name                  : 1-15 characters ; VRF name
address-family            : enum {ipv4}
interface                 : interface-name (Ethernet or Port-channel or Vlan interface-name)

mode                      : enum (sm) ; PIM-mode
dr-priority               : Designated router priority. Range (1-4294967295)
hello-interval            : Hello interval in seconds. Range (1-180)
bfd-enabled               : To enable BFD support for PIM on this interface (true/false)
```
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 User Interface
### 3.3.1 Data Models

The following Openconfig yang models are required to support the PIM-SSM (IPv4) feature & IP multicast forwarding table.
* openconfig-network-instance.yang
* openconfig-pim.yang
* openconfig-aft.yang
* openconfig-aft-ipv4.yang

Extensions for PIM configurations are present in
* openconfig-pim-ext.yang

Extensions for IPv4 multicast forwarding table is present in
* openconfig-aft-ext.yang
* openconfig-aft-ipv4-ext.yang

The following Sonic yang is added to support the PIM-SSM (IPv4) feature
* sonic-pim.yang

The following table shows the extensions (shown as addition) and attributes marked as "not supported" (shown as removed) in the Openconfig yang model. The attributes are marked as not supported due to multiple reasons either due to lack of support in FRR or not scoped for current release. More attributes will be added in future releases based on the deployment requirements.

Notations followed in below OC-yang section:
* "+" below indicates, those are the new extensions added to existing OC-yang
* "-" below indicates, those are the yang attributes that will be marked as not-supported
* If both "+" & "-" is not present, then those are the existing OC-yang attributes from community

```diff
PIM-SSM (IPv4) Configuration Openconfig Model:
==============================================

module: openconfig-network-instance.yang
module: openconfig-pim.yang
module: openconfig-pim-ext.yang


    +--rw network-instances
       +--rw network-instance* [name]
          +--rw name                       -> ../config/name

          ...

          +--rw protocols
             +--rw protocol* [identifier name]
                +--rw identifier                            -> ../config/identifier
                +--rw name                                  -> ../config/name

                ...

                +--rw pim
                   +--rw global
                      +--rw ssm
                         +--rw config
                            +--rw ssm-ranges?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
                         +--ro state
                            +--ro ssm-ranges?   -> /oc-rpol:routing-policy/defined-sets/prefix-sets/prefix-set/name
-                     +--rw rendezvous-points
-                        +--rw rendezvous-point* [address]
-                           +--rw address    -> ../config/address
-                           +--rw config
-                              +--rw address?            inet:ipv4-address
-                              +--rw multicast-groups?   string
-                           +--ro state
-                              +--ro address?            inet:ipv4-address
-                              +--ro multicast-groups?   string                  
                      +--ro state
-                        +--ro neighbor-count?                      uint8
-                        +--ro counters
-                           +--ro hello-messages?        uint32
-                           +--ro join-prune-messages?   uint32
-                           +--ro bootstrap-messages?    uint32
+                        +--ro oc-pim-ext:join-prune-interval?      uint16
+                        +--ro oc-pim-ext:keep-alive-timer?         uint16
+                        +--ro oc-pim-ext:ecmp-enabled?             boolean
+                        +--ro oc-pim-ext:ecmp-rebalance-enabled?   boolean
-                        +--ro sources-joined
-                           +--ro source* [address]
-                              +--ro address    -> ../state/address
-                              +--ro state
-                                 +--ro address?                 inet:ipv4-address
-                                 +--ro group?                   inet:ipv4-address
-                                 +--ro upstream-interface-id?   oc-if:interface-id
+                     +--rw oc-pim-ext:config
+                        +--rw oc-pim-ext:join-prune-interval?      uint16
+                        +--rw oc-pim-ext:keep-alive-timer?         uint16
+                        +--rw oc-pim-ext:ecmp-enabled?             boolean
+                        +--rw oc-pim-ext:ecmp-rebalance-enabled?   boolean
+                     +--ro oc-pim-ext:tib
+                        +--ro oc-pim-ext:ipv4-entries
+                           +--ro oc-pim-ext:ipv4-entry* [group-address]
+                              +--ro oc-pim-ext:group-address    -> ../state/group-address
+                              +--ro oc-pim-ext:state
+                                 +--ro oc-pim-ext:group-address?   oc-inet:ipv4-address
+                                 +--ro oc-pim-ext:src-entries
+                                    +--ro oc-pim-ext:src-entry* [source-address route-type]
+                                       +--ro oc-pim-ext:source-address    -> ../state/source-address
+                                       +--ro oc-pim-ext:route-type        -> ../state/route-type
+                                       +--ro oc-pim-ext:state
+                                          +--ro oc-pim-ext:source-address?       oc-inet:ipv4-address
+                                          +--ro oc-pim-ext:route-type?           route-type
+                                          +--ro oc-pim-ext:incoming-interface?   oc-if:interface-id
+                                          +--ro oc-pim-ext:uptime?               oc-types:timeticks64
+                                          +--ro oc-pim-ext:expiry?               oc-types:timeticks64
+                                          +--ro oc-pim-ext:flags?                string
+                                          +--ro oc-pim-ext:oil-info-entries
+                                             +--ro oc-pim-ext:oil-info-entry* [outgoing-interface]
+                                                +--ro oc-pim-ext:outgoing-interface    -> ../state/outgoing-interface
+                                                +--ro oc-pim-ext:state
+                                                   +--ro oc-pim-ext:outgoing-interface?   oc-if:interface-id
+                                                   +--ro oc-pim-ext:uptime?               oc-types:timeticks64
+                                                   +--ro oc-pim-ext:expiry?               oc-types:timeticks64
+                                          +--ro oc-pim-ext:rpf-info
+                                             +--ro oc-pim-ext:state
+                                                +--ro oc-pim-ext:rpf-neighbor-address?   oc-inet:ipv4-address
+                                                +--ro oc-pim-ext:metric?                 uint32
+                                                +--ro oc-pim-ext:preference?             uint32
                   +--rw interfaces
                      +--rw interface* [interface-id]
                         +--rw interface-id    -> ../config/interface-id
                         +--rw config
-                           +--rw enabled?                  boolean
                            +--rw interface-id?             oc-if:interface-id
                            +--rw mode?                     identityref
-                           +--rw bsr-border?               boolean
-                           +--rw border-router?            boolean
                            +--rw dr-priority?              uint32
-                           +--rw join-prune-interval?      oc-pim-types:pim-interval-type
                            +--rw hello-interval?           uint8
-                           +--rw dead-timer?               uint16
+                           +--rw oc-pim-ext:bfd-enabled?   boolean
                         +--ro state
                            +--ro enabled?                  boolean
                            +--ro interface-id?             oc-if:interface-id
                            +--ro mode?                     identityref
-                           +--ro bsr-border?               boolean
-                           +--ro border-router?            boolean
                            +--ro dr-priority?              uint32
-                           +--ro join-prune-interval?      oc-pim-types:pim-interval-type
                            +--ro hello-interval?           uint8
-                           +--ro dead-timer?               uint16                        
-                           +--ro counters
-                              +--ro hello-messages?        uint32
-                              +--ro join-prune-messages?   uint32
-                              +--ro bootstrap-messages?    uint32
+                           +--ro oc-pim-ext:bfd-enabled?     boolean
+                           +--ro oc-pim-ext:nbrs-count?      uint16
+                           +--ro oc-pim-ext:local-address?   oc-inet:ipv4-address
+                           +--ro oc-pim-ext:dr-address?      oc-inet:ipv4-address
                         +--ro neighbors
                            +--ro neighbor* [neighbor-address]
                               +--ro neighbor-address    -> ../state/neighbor-address
                               +--ro state
                                  +--ro neighbor-address?         inet:ipv4-address
                                  +--ro dr-address?               inet:ipv4-address
                                  +--ro neighbor-established?     oc-types:timeticks64
                                  +--ro neighbor-expires?         oc-types:timeticks64
                                  +--ro mode?                     identityref
+                                 +--ro oc-pim-ext:dr-priority?   uint32
-                        +--rw interface-ref
-                           +--rw config
-                              +--rw interface?      -> /oc-if:interfaces/interface/name
-                              +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
-                           +--ro state
-                              +--ro interface?      -> /oc-if:interfaces/interface/name
-                              +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
```           

```diff

IPv4 Multicast Forwarding table Openconfig Model:
================================================

module: openconfig-network-instance.yang
module: openconfig-aft.yang
module: openconfig-aft-ipv4.yang
module: openconfig-aft-ext.yang
module: openconfig-aft-ipv4-ext.yang


    +--rw network-instances
       +--rw network-instance* [name]
          +--rw name                       -> ../config/name

          ...

          +--rw afts
             +--rw ipv4-unicast

             ...

             +--rw ipv6-unicast

             ...

+            +--rw oc-aft-ipv4-ext:ipv4-multicast
+               +--ro oc-aft-ipv4-ext:ipv4-entries
+                  +--ro oc-aft-ipv4-ext:ipv4-entry* [group-address]
+                     +--ro oc-aft-ipv4-ext:group-address    -> ../state/group-address
+                     +--ro oc-aft-ipv4-ext:state
+                        +--ro oc-aft-ipv4-ext:group-address?   oc-inet:ipv4-address
+                        +--ro oc-aft-ipv4-ext:src-entries
+                           +--ro oc-aft-ipv4-ext:src-entry* [source-address]
+                              +--ro oc-aft-ipv4-ext:source-address    -> ../state/source-address
+                              +--ro oc-aft-ipv4-ext:state
+                                 +--ro oc-aft-ipv4-ext:source-address?       oc-inet:ipv4-address
+                                 +--ro oc-aft-ipv4-ext:incoming-interface?   oc-if:interface-id
+                                 +--ro oc-aft-ipv4-ext:installed?            boolean
+                                 +--ro oc-aft-ipv4-ext:oil-info-entries
+                                    +--ro oc-aft-ipv4-ext:oif-info* [outgoing-interface]
+                                       +--ro oc-aft-ipv4-ext:outgoing-interface    -> ../state/outgoing-interface
+                                       +--ro oc-aft-ipv4-ext:state
+                                          +--ro oc-aft-ipv4-ext:outgoing-interface?   oc-if:interface-id
+                                          +--ro oc-aft-ipv4-ext:uptime?               oc-types:timeticks64
```

```diff
PIM-SSM (IPv4) Configuration Sonic yang Model:
=============================================

module: sonic-pim.yang

+  +--rw sonic-pim
+     +--rw PIM_GLOBALS
+     |  +--rw PIM_GLOBALS_LIST* [vrf-name address-family]
+     |     +--rw vrf-name                  union
+     |     +--rw address-family            enumeration
+     |     +--rw join-prune-interval?      uint16
+     |     +--rw keep-alive-timer?         uint16
+     |     +--rw ssm-ranges?               -> /srpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
+     |     +--rw ecmp-enabled?             boolean
+     |     +--rw ecmp-rebalance-enabled?   boolean
+     +--rw PIM_INTERFACE
+        +--rw PIM_INTERFACE_LIST* [vrf-name address-family interface]
+           +--rw vrf-name          union
+           +--rw address-family    enumeration
+           +--rw interface         union
+           +--rw mode?             enumeration
+           +--rw dr-priority?      uint32
+           +--rw hello-interval?   uint8
+           +--rw bfd-enabled?      boolean
```

### 3.3.2 CLI

#### 3.3.2.1 Configuration Commands

##### 3.3.2.1.1 Global Configuration Commands

The following PIM-SSM (IPv4) global configurations are executed in ```configuration-view```:

All these commands can be executed per VRF. If VRF is not specified, then it will be executed in "default" VRF context. Once PIM global configurations are done on a particular non-default VRF, that VRF cannot be deleted from the system till relevant PIM configurations are cleared.

###### List of Global Configuration commands:
* ip pim [vrf \<vrf-name\>] join-prune-interval <value : (60-600 seconds)>
* no ip pim [vrf \<vrf-name\>] join-prune-interval
* ip pim [vrf \<vrf-name\>] keep-alive-timer <value : (31-60000 seconds)>
* no ip pim [vrf \<vrf-name\>] keep-alive-timer
* ip pim [vrf \<vrf-name\>] ssm prefix-list \<prefix-list-name\>
* no ip pim [vrf \<vrf-name\>] ssm prefix-list
* ip pim [vrf \<vrf-name\>] ecmp [rebalance]
* no ip pim [vrf \<vrf-name\>] ecmp [rebalance]

```
sonic# configure terminal
sonic(config)#

sonic(config)# ip pim
  vrf                  VRF name
  join-prune-interval  Join prune interval in seconds
  keep-alive-timer     Keep alive timer in seconds
  ssm                  Configure SSM mode
  ecmp                 Configure ECMP

sonic(config)#
sonic(config)#
sonic(config)# ip pim vrf Vrf1
  join-prune-interval  Join prune interval in seconds
  keep-alive-timer     Keep alive timer in seconds
  ssm                  Configure SSM mode
  ecmp                 Configure ECMP

sonic(config)#
sonic(config)#
sonic(config)# no ip pim
  vrf                  VRF name
  join-prune-interval  Join prune interval in seconds
  keep-alive-timer     Keep alive timer in seconds
  ssm                  Configure SSM mode
  ecmp                 Configure ECMP mode

sonic(config)#
sonic(config)#
sonic(config)# no ip pim vrf Vrf1
  join-prune-interval  Join prune interval in seconds
  keep-alive-timer     Keep alive timer in seconds
  ssm                  Configure SSM mode
  ecmp                 Configure ECMP mode

sonic(config)#
```

###### Join Prune interval:
```
sonic(config)# ip pim join-prune-interval
  <60..600>  Range 60-600 seconds

sonic(config)# ip pim join-prune-interval 70
sonic(config)# ip pim vrf Vrf1 join-prune-interval 75
sonic(config)#

-------------------------------------------------------

sonic(config)# no ip pim join-prune-interval
  <cr>

sonic(config)# no ip pim join-prune-interval
sonic(config)# no ip pim vrf Vrf1 join-prune-interval
```

###### Keep Alive timer:
Period after last (S,G) data packet during which (S,G) Join state will be even in the absence of (S,G) Join messages.
```
sonic(config)# ip pim keep-alive-timer
  <31..60000>  Range 31-60000 seconds

sonic(config)# ip pim keep-alive-timer 35
sonic(config)# ip pim vrf Vrf1 keep-alive-timer 45
sonic(config)#

--------------------------------------------------------

sonic(config)# no ip pim keep-alive-timer
  <cr>

sonic(config)# no ip pim keep-alive-timer
sonic(config)# no ip pim vrf Vrf1 keep-alive-timer
sonic(config)#

```

###### SSM Prefix-list configuration:
Apart from standard PIM-SSM multicast range (232.0.0.0/8), user can qualify other multicast group address as PIM-SSM range using IP-prefix-list. User should create the corresponding IP-prefix-list using existing "ip prefix-list" CLI command and then associate that prefix-list to PIM through this CLI command. This IP-prefix-list cannot be deleted from the system until after removal of any PIM global configuration referring to the prefix list.
```
sonic(config)# ip pim ssm
  prefix-list  Configure prefix list name

sonic(config)# ip pim ssm prefix-list
  String  Prefix list name

sonic(config)# ip pim ssm prefix-list pim_ssm_pfx_list
sonic(config)# ip pim vrf Vrf1 ssm prefix-list pim_ssm_pfx_list
sonic(config)#

-----------------------------------------------------------------

sonic(config)# no ip pim ssm
  prefix-list  Configure prefix list name

sonic(config)# no ip pim ssm prefix-list
  <cr>

sonic(config)# no ip pim ssm prefix-list
sonic(config)# no ip pim vrf Vrf1 ssm prefix-list
sonic(config)#
```

###### To enable/disable PIM ECMP
If PIM has the a choice of ECMP nexthops for a particular RPF, PIM will cause S,G flows to be spread out amongst the nexthops. If this command is not specified then the first nexthop found will be used.

```
sonic(config)# ip pim ecmp
  rebalance  Enable ECMP rebalance
  <cr>

sonic(config)#
sonic(config)# ip pim ecmp
sonic(config)# ip pim vrf Vrf1 ecmp
sonic(config)#

----------------------------------------

sonic(config)# no ip pim ecmp
  rebalance  Enable ECMP rebalance
  <cr>

sonic(config)# no ip pim ecmp
sonic(config)# no ip pim vrf Vrf1 ecmp
sonic(config)#
```

###### To enable/disable PIM ECMP rebalance
If PIM is using ECMP and an interface goes down, cause PIM to rebalance all S,G flows across the remaining nexthops. If this command is not configured pim only modifies those S,G flows that were using the interface that went down.

To enable/disable this command, PIM ECMP should be enabled first

```
sonic(config)# ip pim ecmp rebalance
  <cr>

sonic(config)# ip pim ecmp rebalance
sonic(config)# ip pim vrf Vrf1 ecmp rebalance
sonic(config)#

-------------------------------------------------

sonic(config)# no ip pim ecmp rebalance
  <cr>

sonic(config)# no ip pim ecmp rebalance
sonic(config)# no ip pim vrf Vrf1 ecmp rebalance
sonic(config)#  
```

##### 3.3.2.1.2 Interface specific Configuration Commands

The following PIM-SSM (IPv4) interface specific configurations are executed in ```interface-view```. All these commands are supported on Ethernet, Port-channel & VLAN interfaces.

###### List of Interface-specific configuration commands:
* ip pim sparse-mode
* no ip pim sparse-mode
* ip pim drpriority <value : (1-4294967295)>
* no ip pim drpriority
* ip pim hello <value : (1-180 seconds)>
* no ip pim hello
* ip pim bfd
* no ip pim bfd

Once PIM interface specific configurations are done on a particular interface, that particular interface cannot be deleted till PIM interface configurations exists on that interface. Interface can be deleted, once PIM interface configurations are cleared.

For "Dynamic Port Breakout" feature, when a particular physical port is breakin/breakout, existing interfaces will be deleted and new set of interfaces will be created. As part of that existing interface delete, relevant PIM configurations on that interface will be cleaned up internally.

VRF change for a particular interface is not allowed, once PIM interface-specific configurations are present in that interface. It should be cleaned up before changing the VRF.

```
PIM interface-specific configurations are supported in Ethernet, Port-channel & VLAN interfaces. Here VLAN interface is shown as an example.

sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(conf-if-Vlan100)# ip pim
  bfd          Enable BFD on PIM
  drpriority   Set the designated router (DR) priority
  hello        Set the hello interval for PIM
  sparse-mode  Enable PIM sparse-mode

sonic(conf-if-Vlan100)#

----------------------------------------------------------

sonic(conf-if-Vlan100)# no ip pim
  bfd          Disable BFD on PIM
  drpriority   Clear the designated router (DR) priority
  hello        Clear the hello interval for PIM
  sparse-mode  Disable PIM sparse-mode

sonic(conf-if-Vlan100)#
```

###### To enable/disable PIM Sparse-mode:
```
sonic(conf-if-Vlan100)# ip pim sparse-mode
  <cr>

sonic(conf-if-Vlan100)# ip pim sparse-mode
sonic(conf-if-Vlan100)#

---------------------------------------------

sonic(conf-if-Vlan100)# no ip pim sparse-mode
  <cr>

sonic(conf-if-Vlan100)# no ip pim sparse-mode
sonic(conf-if-Vlan100)#
```

###### To set Designated router priority:
Set the DR Priority for the PIM interface. This command allows user to set the priority of a node for becoming a DR. A higher value means higher chances of being elected.
```
sonic(config)# interface Vlan 100
sonic(conf-if-Vlan100)# ip pim drpriority
  <1..4294967295>  Range 1_4294967295

sonic(conf-if-Vlan100)# ip pim drpriority 10
sonic(conf-if-Vlan100)#

---------------------------------------------

sonic(conf-if-Vlan100)# no ip pim drpriority
  <cr>

sonic(conf-if-Vlan100)# no ip pim drpriority
sonic(conf-if-Vlan100)#
```

###### Hello interval:
Periodic interval for Hello messages to keep the PIM neighbor session alive. This configuration internally configures the default hold-time (3.5 * Hello-interval) ; the period to keep the PIM neighbor session alive even without hello messages from that particular neighbor.
```
sonic(conf-if-Vlan100)# ip pim hello
  <1..180>  Range 1 to 180 in seconds

sonic(conf-if-Vlan100)# ip pim hello 30
sonic(conf-if-Vlan100)#

----------------------------------------

sonic(conf-if-Vlan100)# no ip pim hello
  <cr>

sonic(conf-if-Vlan100)# no ip pim hello
sonic(conf-if-Vlan100)#
```

###### To enable BFD Support for PIM on interface:
This command will be used to enable/disable BFD support for PIM on interface
```
sonic(conf-if-Vlan100)# ip pim bfd
  <cr>

sonic(conf-if-Vlan100)# ip pim bfd
sonic(conf-if-Vlan100)#

--------------------------------------

sonic(conf-if-Vlan100)# no ip pim bfd
  <cr>

sonic(conf-if-Vlan100)# no ip pim bfd
sonic(conf-if-Vlan100)#
```

#### 3.3.2.2 Show Commands

###### 3.3.2.2.1 Global Multicast Show commands

List of Global Multicast show Commands
* show ip mroute [vrf {<vrf-name> | all}] [<Group-addr> | {<Group-addr>   <Source-addr>}]
* show ip mroute [vrf {<vrf-name> | all}] summary

Here sample show commands o/p are shown for "default" VRF. But these commands support display for non-default VRF as well. Also there is an option to display details about all VRFs using "vrf all" option and it might be useful for "show tech-support"

```
show ip mroute [vrf {<vrf-name> | all}] [<Group-addr> | {<Group-addr>   <Source-addr>}]
=======================================================================================

sonic# show ip mroute
IP Multicast Routing Table for VRF: default
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 71.0.0.11       233.0.0.1       Vlan100       Vlan200       00:41:59
* 71.0.0.22       233.0.0.1       Vlan100       Vlan200       00:41:54
                                                Vlan201       00:41:59
* 71.0.0.11       234.0.0.1       Vlan100       Vlan200       00:41:34
* 71.0.0.33       234.0.0.1       Vlan100       Vlan200       00:41:31
                                                Vlan201       00:41:44
* 71.0.0.22       235.0.0.1       Vlan100       Vlan200       00:41:16
* 71.0.0.33       235.0.0.1       Vlan100       Vlan200       00:41:14

--------------------------------------------------------------------------------

sonic# show ip mroute 233.0.0.1
IP Multicast Routing Table for VRF: default
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 71.0.0.11       233.0.0.1       Vlan100       Vlan200       00:41:59
* 71.0.0.22       233.0.0.1       Vlan100       Vlan200       00:41:54
                                                Vlan201       00:41:59

--------------------------------------------------------------------------------

sonic# show ip mroute 233.0.0.1 71.0.0.22
IP Multicast Routing Table for VRF: default
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 71.0.0.22       233.0.0.1       Vlan100       Vlan200       00:41:54
                                                Vlan201       00:41:59
------------------------------------------------------------------------------

sonic# show ip mroute vrf Vrf1
IP Multicast Routing Table for VRF: Vrf1
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 51.0.0.11       233.0.0.1       Vlan300       Vlan301       00:41:59
* 51.0.0.22       233.0.0.1       Vlan300       Vlan301       00:41:54
                                                Vlan302       00:41:59

--------------------------------------------------------------------------------

sonic# show ip mroute vrf all
IP Multicast Routing Table for VRF: default
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 71.0.0.11       233.0.0.1       Vlan100       Vlan200       00:41:59
* 71.0.0.22       233.0.0.1       Vlan100       Vlan200       00:41:54
                                                Vlan201       00:41:59
* 71.0.0.11       234.0.0.1       Vlan100       Vlan200       00:41:34
* 71.0.0.33       234.0.0.1       Vlan100       Vlan200       00:41:31
                                                Vlan201       00:41:44
* 71.0.0.22       235.0.0.1       Vlan100       Vlan200       00:41:16
* 71.0.0.33       235.0.0.1       Vlan100       Vlan200       00:41:14

IP Multicast Routing Table for VRF: Vrf1
  * -> indicates installed route

  Source          Group           Input         Output        Uptime
* 51.0.0.11       233.0.0.1       Vlan300       Vlan301       00:41:59
* 51.0.0.22       233.0.0.1       Vlan300       Vlan301       00:41:54
                                                Vlan302       00:41:59
```

```
show ip mroute [vrf {<vrf-name> | all}] summary
===============================================

sonic# show ip mroute summary
IP Multicast Routing Table summary for VRF: default

Mroute Type      Installed/Total
(S, G)           6/6

--------------------------------------------------------------------------------

sonic# show ip mroute vrf Vrf1 summary
IP Multicast Routing Table summary for VRF: Vrf1

Mroute Type      Installed/Total
(S, G)           2/2

--------------------------------------------------------------------------------

sonic# show ip mroute vrf all summary
IP Multicast Routing Table summary for VRF: default

Mroute Type      Installed/Total
(S, G)           6/6

IP Multicast Routing Table summary for VRF: Vrf1

Mroute Type      Installed/Total
(S, G)           2/2
```

###### 3.3.2.2.2 PIM-SSM (IPv4) Show commands

List of PIM-SSM (IPv4) show Commands:
* show ip pim [vrf {<vrf-name> | all}] interface [<intf-name>]
* show ip pim [vrf {<vrf-name> | all}] neighbor [<ipv4-nbr-address>]
* show ip pim [vrf {<vrf-name> | all}] ssm
* show ip pim [vrf {<vrf-name> | all}] topology [<Group-addr> | {<Group-addr>   <Source-addr>}]
* show ip pim [vrf {<vrf-name> | all}] rpf

If VRF is not mentioned, then command will be executed in "default" VRF context.

Here sample show commands o/p are shown for "default" VRF. But these commands support display for non-default VRF as well. Also there is an option to display details about all VRFs using "vrf all" option and it might be useful for "show tech-support"

```
show ip pim [vrf {<vrf-name> | all}] interface [<intf-name>]
============================================================

sonic # show ip pim interface
PIM Interface information for VRF: default

Interface       State       Address         PIM Nbrs       PIM DR          Hello-interval       PIM DR-Priority
Vlan100         up          100.0.0.2       1              100.0.0.2       30                   1
Vlan200         up          200.0.0.2       1              200.0.0.3       30                   1

----------------------------------------------------------------------------------------------------------------

sonic # show ip pim interface vlan 100
PIM Interface information for VRF: default

Interface       State       Address         PIM Nbrs       PIM DR          Hello-interval       PIM DR-Priority
Vlan100         up          100.0.0.2       1              100.0.0.2       30                   1

----------------------------------------------------------------------------------------------------------------

sonic # show ip pim vrf Vrf1 interface
PIM Interface information for VRF: Vrf1

Interface       State       Address         PIM Nbrs       PIM DR          Hello-interval       PIM DR-Priority
Vlan300         up          30.0.0.2        1              30.0.0.2        30                   1

----------------------------------------------------------------------------------------------------------------

sonic # show ip pim vrf all interface
PIM Interface information for VRF: default

Interface       State       Address         PIM Nbrs       PIM DR          Hello-interval       PIM DR-Priority
Vlan100         up          100.0.0.2       1              100.0.0.2       30                   1
Vlan200         up          200.0.0.2       1              200.0.0.3       30                   1

PIM Interface information for VRF: Vrf1

Interface       State       Address         PIM Nbrs       PIM DR          Hello-interval       PIM DR-Priority
Vlan300         up          30.0.0.2        1              30.0.0.2        30                   1
```

```
show ip pim [vrf {<vrf-name> | all}] neighbor [<ipv4-nbr-address>]
==================================================================

sonic# show ip pim neighbor
PIM Neighbor information for VRF: default

Interface       Neighbor        Uptime         Expirytime       DR-Priority
Vlan100         100.0.0.1       01:38:52       00:01:22         1
Vlan200         200.0.0.3       01:22:33       00:01:13         1

--------------------------------------------------------------------------------

sonic# show ip pim neighbor 100.0.0.1
PIM Neighbor information for VRF: default

Interface       Neighbor        Uptime         Expirytime       DR-Priority
Vlan100         100.0.0.1       01:38:52       00:01:22         1

--------------------------------------------------------------------------------

sonic# show ip pim vrf Vrf1 neighbor
PIM Neighbor information for VRF: Vrf1

Interface       Neighbor        Uptime         Expirytime       DR-Priority
Vlan300         30.0.0.1        01:48:32       00:01:12         1

--------------------------------------------------------------------------------

sonic# show ip pim vrf all neighbor
PIM Neighbor information for VRF: default

Interface       Neighbor        Uptime         Expirytime       DR-Priority
Vlan100         100.0.0.1       01:38:52       00:01:22         1
Vlan200         200.0.0.3       01:22:33       00:01:13         1

PIM Neighbor information for VRF: Vrf1

Interface       Neighbor        Uptime         Expirytime       DR-Priority
Vlan300         30.0.0.1        01:48:32       00:01:12         1
```

```
show ip pim [vrf {<vrf-name> | all}] ssm
========================================

If IP-prefix list is associated:
===============================
sonic# show ip pim ssm
PIM SSM information for VRF: default

SSM group range : PIM_PLIST1

-----------------------------------------

If IP-prefix list is not associated:
===================================
sonic# show ip pim ssm
PIM SSM information for VRF: default

SSM group range : 232.0.0.0/8

-----------------------------------------

sonic# show ip pim vrf Vrf1 ssm
PIM SSM information for VRF: Vrf1

SSM group range : PIM_PLIST1

-----------------------------------------

sonic# show ip pim vrf all ssm
PIM SSM information for VRF: default

SSM group range : PIM_PLIST1

PIM SSM information for VRF: Vrf1

SSM group range : PIM_PLIST1
```

```
show ip pim [vrf {<vrf-name> | all}] topology [<Group-addr> | {<Group-addr>   <Source-addr>}]
=============================================================================================

sonic# show ip pim topology
PIM Multicast Routing Table for VRF: default

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(71.0.0.11, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:07:50/00:01:39
    vlan122   uptime/expiry-time: 12:33:21/--:--:--

(71.0.0.22, 233.0.0.1), uptime 13:08:45, expires 00:00:18, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:22:52/00:01:45
    vlan124   uptime/expiry-time: 12:42:28/--:--:--

(101.0.0.22, 225.1.1.1), uptime 13:07:51, expires 00:06:09, flags SCJT
  Incoming interface: vlan105, RPF neighbor 105.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:03:50/00:01:39
    vlan123   uptime/expiry-time: 13:02:40/--:--:--

--------------------------------------------------------------------------------

sonic# show ip pim topology 233.0.0.1
PIM Multicast Routing Table for VRF: default

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(71.0.0.11, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:07:50/00:01:39
    vlan122   uptime/expiry-time: 12:33:21/--:--:--

(71.0.0.22, 233.0.0.1), uptime 13:08:45, expires 00:00:18, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:22:52/00:01:45
    vlan124   uptime/expiry-time: 12:42:28/--:--:--

--------------------------------------------------------------------------------

sonic# show ip pim topology 225.1.1.1 101.0.0.22
PIM Multicast Routing Table for VRF: default

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(101.0.0.22, 225.1.1.1), uptime 13:07:51, expires 00:06:09, flags SCJT
  Incoming interface: vlan105, RPF neighbor 105.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:03:50/00:01:39
    vlan123   uptime/expiry-time: 13:02:40/--:--:--

--------------------------------------------------------------------------------

sonic# show ip pim vrf Vrf1 topology
PIM Multicast Routing Table for VRF: Vrf1

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(51.0.0.11, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
Incoming interface: vlan300, RPF neighbor 30.0.0.1
Outgoing interface list:
vlan301   uptime/expiry-time: 13:07:50/00:01:39

(51.0.0.22, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
Incoming interface: vlan300, RPF neighbor 30.0.0.1
Outgoing interface list:
vlan301   uptime/expiry-time: 13:07:50/00:01:39
vlan302   uptime/expiry-time: 14:07:50/00:01:29

--------------------------------------------------------------------------------

sonic# show ip pim vrf all topology
PIM Multicast Routing Table for VRF: default

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(71.0.0.11, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:07:50/00:01:39
    vlan122   uptime/expiry-time: 12:33:21/--:--:--

(71.0.0.22, 233.0.0.1), uptime 13:08:45, expires 00:00:18, flags SCJT
  Incoming interface: vlan100, RPF neighbor 100.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:22:52/00:01:45
    vlan124   uptime/expiry-time: 12:42:28/--:--:--

(101.0.0.22, 225.1.1.1), uptime 13:07:51, expires 00:06:09, flags SCJT
  Incoming interface: vlan105, RPF neighbor 105.0.0.1
  Outgoing interface list:
    vlan200   uptime/expiry-time: 13:03:50/00:01:39
    vlan123   uptime/expiry-time: 13:02:40/--:--:--

PIM Multicast Routing Table for VRF: Vrf1

"Flags: S - Sparse, C - Connected, L - Local, P - Pruned,
R - RP-bit set, F - Register Flag, T - SPT-bit set, J - Join SPT,
K - Ack-Pending state"

(51.0.0.11, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
Incoming interface: vlan300, RPF neighbor 30.0.0.1
Outgoing interface list:
vlan301   uptime/expiry-time: 13:07:50/00:01:39

(51.0.0.22, 233.0.0.1), uptime 13:08:24, expires 00:00:12, flags SCJT
Incoming interface: vlan300, RPF neighbor 30.0.0.1
Outgoing interface list:
vlan301   uptime/expiry-time: 13:07:50/00:01:39
vlan302   uptime/expiry-time: 14:07:50/00:01:29
```

```
show ip pim [vrf {<vrf-name> | all}] rpf
========================================

sonic# show ip pim rpf
PIM RPF information for VRF: default

Source          Group           RpfIface       RpfAddress       RibNextHop       Metric       Pref
71.0.0.11       233.0.0.1       Vlan100        100.0.0.1        100.0.0.1        0            1
71.0.0.22       235.0.0.1       Vlan100        100.0.0.1        100.0.0.1        0            1

---------------------------------------------------------------------------------------------------

sonic# show ip pim vrf Vrf1 rpf
PIM RPF information for VRF: Vrf1

Source          Group           RpfIface       RpfAddress       RibNextHop       Metric       Pref
51.0.0.11       233.0.0.1       Vlan300        30.0.0.1         30.0.0.1         0            1
51.0.0.22       235.0.0.1       Vlan300        30.0.0.1         30.0.0.1         0            1

---------------------------------------------------------------------------------------------------

sonic# show ip pim vrf all rpf
PIM RPF information for VRF: default

Source          Group           RpfIface       RpfAddress       RibNextHop       Metric       Pref
71.0.0.11       233.0.0.1       Vlan100        100.0.0.1        100.0.0.1        0            1
71.0.0.22       235.0.0.1       Vlan100        100.0.0.1        100.0.0.1        0            1

PIM RPF information for VRF: Vrf1

Source          Group           RpfIface       RpfAddress       RibNextHop       Metric       Pref
51.0.0.11       233.0.0.1       Vlan300        30.0.0.1         30.0.0.1         0            1
51.0.0.22       235.0.0.1       Vlan300        30.0.0.1         30.0.0.1         0            1
```

#### 3.3.2.3 show running-config & show configuration

Show running-config and show configuration will be enhanced to display the PIM-SSM (IPv4) Global & interface-specific configurations

###### 3.3.2.3.1 show running-config

Here is the sample "show running-config" output for PIM-SSM (Ipv4) global configurations

###### Global configurations:
```
sonic# show running-configuration

ip pim vrf default join-prune-interval 70
ip pim vrf default keep-alive-timer 35
ip pim vrf default ssm prefix-list pim_ssm_pfx_list
ip pim vrf default ecmp
ip pim vrf default ecmp rebalance
ip pim vrf Vrf1 join-prune-interval 80
ip pim vrf Vrf1 keep-alive-timer 45
ip pim vrf Vrf1 ssm prefix-list pim_ssm_pfx_list
ip pim vrf Vrf1 ecmp
ip pim vrf Vrf1 ecmp rebalance
```

###### Interface-specific configurations:
```
sonic# show running-configuration

interface Vlan100
 ip pim sparse-mode
 ip pim drpriority 20
 ip pim hello 25
 ip pim bfd
!
interface Ethernet216
 ip pim sparse-mode
 ip pim drpriority 10
 ip pim hello 20
 ip pim bfd
!
interface PortChannel 1
ip pim sparse-mode
ip pim drpriority 20
ip pim hello 25
ip pim bfd
!
```

###### 3.3.2.3.2 show configuration

**"show configuration"** command will be enhanced under interface-mode to display the PIM-SSM (IPv4) configurations as well. The sample output is shown below for reference

```
sonic(config)# interface Vlan 100
sonic(conf-if-Vlan100)# show configuration
!
interface Vlan100
 ip pim sparse-mode
 ip pim drpriority 20
 ip pim hello 25
 ip pim bfd
!
sonic(conf-if-Vlan100)#

sonic(config)# interface Ethernet 216
sonic(conf-if-Ethernet216)# show configuration
!
interface Ethernet216
 ip pim sparse-mode
 ip pim drpriority 10
 ip pim hello 20
 ip pim bfd
sonic(conf-if-Ethernet216)#

sonic(config)# interface PortChannel 1
sonic(conf-if-po1)# show configuration
!
interface PortChannel 1
ip pim sparse-mode
ip pim drpriority 20
ip pim hello 25
ip pim bfd
sonic(conf-if-po1)#
```

#### 3.3.2.4 Debug Commands

###### 3.3.2.4.1 Global Multicast Clear commands

* **clear ip mroute [vrf \<vrf-name\>]** ==> To reset all IP Multicast routes for the particular VRF

###### 3.3.2.3.2 PIM-SSM (IPv4) Clear commands

* **clear ip pim [vrf \<vrf-name\>] interfaces** ==> To reset all PIM interfaces of a particular VRF

* **clear ip pim [vrf \<vrf-name\>] oil** ==> To rescan PIM OIL (Outgoing Interfaces List) of all multicast entries of a particular VRF


#### 3.3.2.5 IS-CLI Compliance
All CLI commands mentioned above follows IS-CLI Compliance.

### 3.3.3 REST API Support
Various REST operations (POST/PUT/PATCH/GET/DELETE) will be supported for PIM-SSM (IPv4) using OC yang configuration objects & state objects.

Sample REST configurations & delete operations are present here as reference for global PIM-SSM objects

```
curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Content-Type: application/yang
-data+json" -d "{ \"openconfig-network-instance:global\": { \"openconfig-pim-ext:config\": { \"join-prune-interval\": 65 } } }" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global/openconfig-pim-ext:config/join-prune-interval" | py
thon -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Content-Type: application/yang
-data+json" -d "{ \"openconfig-network-instance:global\": { \"openconfig-pim-ext:config\": { \"keep-alive-timer\": 35 } } }" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global/openconfig-pim-ext:config/keep-alive-timer" | pytho
n -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Content-Type: application/yang
-data+json" -d "{ \"openconfig-network-instance:global\": { \"ssm\": { \"config\": { \"ssm-ranges\": \"pim_pfx_list_1\" } } } }" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global/ssm/config/ssm-ranges" | python -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Content-Type: application/yang
-data+json" -d "{ \"openconfig-network-instance:global\": { \"openconfig-pim-ext:config\": { \"ecmp-enabled\": true } } }" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global/openconfig-pim-ext:config/ecmp-enabled" | python -m
 json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global" -H "accept: */*" -H "Content-Type: application/yang
-data+json" -d "{ \"openconfig-network-instance:global\": { \"openconfig-pim-ext:config\": { \"ecmp-rebalance-enabled\": true } } }" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/global/openconfig-pim-ext:config/ecmp-rebalance-enabled" | python -m json.tool
```

Sample REST configurations & delete operations are present here as reference for interface-specific PIM-SSM objects

```
curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/mode" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"mode\": \"PIM_MODE_SPARSE\"}" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/mode" | python -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/dr-priority" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"dr-priority\": 10}" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/dr-priority" | python -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/hello-interval" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"hello-interval\": 3}" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/hello-interval" | python -m json.tool


curl -X PATCH -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/openconfig-pim-ext:bfd-enabled" -H "accept: */*" -H "Content-Type: application/yang-data+json" -d "{\"bfd-enabled\": true}" | python -m json.tool

curl -X DELETE -ku admin:admin "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim/interfaces/interface=Ethernet0/config/vaol" | python -m json.tool
```

Sample REST GET operation for whole PIM OC objects

```
curl -X GET -ku admin:admin https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=PIM,pim/pim | python -m json.tool
```

### 3.3.4 gNMI Support
Various gNMI operations will be supported for PIM-SSM (IPv4) using OC yang configuration objects & state objects.


# 4 Flow Diagrams
# 5 Error Handling
# 6 Serviceability and Debug
# 7 Warm Boot Support

# 8 Unit Test
* All PIM global & interface-specific configuration will be tested through CLI/REST/gNMI
* All PIM global & interface-specific configuration delete will be tested through CLI/REST/gNMI
* All CLI show commands will be tested
* OC yang objects GET will be tested through REST/gNMI
* show running-config will be tested
* Config save & restore will be tested for all PIM global & interface-specific configurations
