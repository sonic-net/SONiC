  
  

# BGP EVPN IS-CLI 
  
IS-CLIs for BGP EVPN config and show commands  
  
# High Level Design Document  
  
#### Rev 0.1  
  
  
  
# Table of Contents  
  
* [List of Tables](#list-of-tables)  
  
* [Revision](#revision)  
  
* [About This Manual](#about-this-manual)  
  
* [Scope](#scope)  
  
* [Definition/Abbreviation](#definitionabbreviation)  
  
  
  
# List of Tables  
  
[Table 1: Abbreviations](#table-1-abbreviations)  
  
  
  
# Revision  
  
| Rev | Date | Author | Change Description |  
  
|:---:|:-----------:|:------------------:|-----------------------------------|  
  
| 0.1 | 12/22/2019 | Sayed Saquib | Initial version |  
  
  
  
# About this Manual  
  
This document provides information about the northbound interface details for BGP EVPN CLIs.  
  
  
  
# Scope  
  
This document covers the "configuration" and "show" commands supported for BGP EVPN. BGP openconfig model is extended to support BGP EVPN CLIs  
  
  
  
# Definition/Abbreviation  
  
  
  
### Table 1: Abbreviations  
  
| **Term** | **Meaning** |  
  
|--------------------------|-------------------------------------|  
  
| BGP | Border Gateway Protocol |  
| EVPN | Ethernet Virtual Private Network |  
  
# 1 Feature Overview  
  
Add support for BGP EVPN create/set/get via CLI, REST and gNMI using  sonic-mgmt-framework container  
  
  
  
## 1.1 Requirements  
  
Provide management framework capabilities to handle:  
  
- BGP EVPN configuration  
  
- BGP EVPN VNI and ROUTE query.  
  
  
  
### 1.1.1 Functional Requirements  
  
  
  
Provide management framework support to existing SONiC capabilities with respect to BGP EVPN.  
  
  
  
### 1.1.2 Configuration and Management Requirements  
  
- CLI configuration and show commands  
  
- REST API support  
  
- gNMI Support  
  
  
  
Details described in Section 3.  
  
  
  
## 1.2 Design Overview  
  
  
  
### 1.2.1 Basic Approach  
  
For Config parameters:
Design DB schema for BGP EVPN config parameters
Extend Openconfig BGP model with BGP EVPN parameters
Implement transformer for BGP OC model to DB schema  

For Show command:
Extend Openconfig BGP model with BGP EVPN state parameters
Extend Openconfig BGP RIB model for BGP EVPN RIB
Implement transformer to fill BGP RIB GET request by fetching information through show commands available in BGP docker
  
  
### 1.2.2 Container  
  
- Most code changes will be done in sonic-management-framework container 

- sonic-buildimage container will contain changes to handle configDB updates

- bgp container will contain minor changes/fix to support show commands fetching for GET operations
  
  
  
### 1.2.3 SAI Overview  
  
N/A  
  
  
  
# 2 Functionality  
  
## 2.1 Target Deployment Use Cases  
  
Manage/configure BGP EVPN via CLI, gNMI and REST interfaces  
  
## 2.2 Functional Description  
  
Provide CLI, gNMI and REST support for BGP EVPN related commands handling  
  
  
  
# 3 Design  
  
## 3.1 Overview  
  
1. Transformer common app owns the Open config data models related to BGP EVPN (which means no separate app module required for handling BGP EVPN yang objects).  
  
    - openconfig-bgp-evpn-ext.yang  

2. Provide annotations for required objects so that transformer core and common app will take care of handling them.  
    - openconfig-network-instance-annot.yang
  
3. Provide transformer methods as per the annotations defined to take care of model specific logics and validations.  
    - xfmr_bgp_evpn_vni.go
  
4. Define SONiC YANG and Redis ABNF schema for the supported BGP EVPN config commands.  
    - sonic-bgp-global.yang
  
5. In bgpcfgd register for Redis DB events for the BGP EVPN objects, so as to translate the Redis DB events to FRR-BGP CLI commands to configure EVPN
  
6. Provide KLISH based CLI commands 
    - bgp_af_l2vpn.xml
    - bgp_af_l2vpn_vni.xml
    
7. Actioner scripts for config and show commands
    - sonic-cli-bgp-evpn.py
    - sonic-cli-show-bgp-evpn.py
8. Renderer for show commands 
    - show_evpn_vni.j2
    - show_evpn_routes.j2
  
## 3.2 User Interface  
  
### 3.2.1 Data Models  
  
List of yang models required for BGP EVPN management.  
openconfig-bgp-evpn-ext.yang

This yang extends the BGP OC yang model [openconfig-bgp.yang]([https://github.com/openconfig/public/blob/master/release/models/bgp/openconfig-bgp.yang](https://github.com/openconfig/public/blob/master/release/models/bgp/openconfig-bgp.yang))  
  
Supported yang objects and attributes are as per below tree: 

BGP EVPN config: 
  
```diff  
  
module: openconfig-bgp-evpn-ext  
  
        |     |  |  |     +--rw l2vpn-evpn

+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:advertise-all-vni?      boolean
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:advertise-list*         identityref
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:advertise-default-gw?   boolean
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:route-distinguisher?    string
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:vpn-target* [route-target]
+       |     |  |  |     |  |  +--rw oc-bgp-evpn-ext:route-target         rt-types:route-target
+       |     |  |  |     |  |  +--rw oc-bgp-evpn-ext:route-target-type    rt-types:route-target-type
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:vnis
+       |     |  |  |     |  |  +--rw oc-bgp-evpn-ext:vni* [vni-number]
+       |     |  |  |     |  |     +--rw oc-bgp-evpn-ext:vni-number              -> ../config/vni-number
+       |     |  |  |     |  |     +--rw oc-bgp-evpn-ext:config
+       |     |  |  |     |  |     |  +--rw oc-bgp-evpn-ext:vni-number?   uint32
+       |     |  |  |     |  |     +--ro oc-bgp-evpn-ext:state
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:vni-number?            uint32
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:type?                  string
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:is-live?               boolean
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:originator?            string
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:mcast-group?           string
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:advertise-gw-mac?      boolean
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:import-rts*            string
+       |     |  |  |     |  |     |  +--ro oc-bgp-evpn-ext:export-rts*            string
+       |     |  |  |     |  |     +--rw oc-bgp-evpn-ext:advertise-default-gw?   boolean
+       |     |  |  |     |  |     +--rw oc-bgp-evpn-ext:route-distinguisher?    string
+       |     |  |  |     |  |     +--rw oc-bgp-evpn-ext:vpn-target* [route-target]
+       |     |  |  |     |  |        +--rw oc-bgp-evpn-ext:route-target         rt-types:route-target
+       |     |  |  |     |  |        +--rw oc-bgp-evpn-ext:route-target-type    rt-types:route-target-type
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:default-originate
+       |     |  |  |     |  |  +--rw oc-bgp-evpn-ext:ipv4?   boolean
+       |     |  |  |     |  |  +--rw oc-bgp-evpn-ext:ipv6?   boolean
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:autort?                 enumeration
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:flooding?               enumeration
+       |     |  |  |     |  +--rw oc-bgp-evpn-ext:dup-addr-detection
+       |     |  |  |     |     +--rw oc-bgp-evpn-ext:enabled?     boolean
+       |     |  |  |     |     +--rw oc-bgp-evpn-ext:max-moves?   uint32
+       |     |  |  |     |     +--rw oc-bgp-evpn-ext:time?        uint32
+       |     |  |  |     |     +--rw oc-bgp-evpn-ext:freeze?      union
  
```  

BGP RIB for EVPN:

```diff  
  
module: openconfig-bgp-evpn-ext  

+       |     |     |     +--ro oc-bgp-evpn-ext:l2vpn-evpn
+       |     |     |     |  +--ro oc-bgp-evpn-ext:loc-rib
+       |     |     |     |  |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |  +--ro oc-bgp-evpn-ext:routes
+       |     |     |     |  |     +--ro oc-bgp-evpn-ext:route* [route-distinguisher prefix]
+       |     |     |     |  |        +--ro oc-bgp-evpn-ext:route-distinguisher    -> ../state/route-distinguisher
+       |     |     |     |  |        +--ro oc-bgp-evpn-ext:prefix                 -> ../state/prefix
+       |     |     |     |  |        +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:prefix?                string
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:origin?                union
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:path-id?               uint32
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:last-modified?         oc-types:timeticks64
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:valid-route?           boolean
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:invalid-reason?        identityref
-       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:attr-index?            -> ../../../../../../../../attr-sets/attr-set/state/index
-       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:community-index?       -> ../../../../../../../../communities/community/state/index
-       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:ext-community-index?   -> ../../../../../../../../ext-communities/ext-community/state/index
+       |     |     |     |  |        +--ro oc-bgp-evpn-ext:unknown-attributes
+       |     |     |     |  |        |  +--ro oc-bgp-evpn-ext:unknown-attribute* [attr-type]
+       |     |     |     |  |        |     +--ro oc-bgp-evpn-ext:attr-type    -> ../state/attr-type
+       |     |     |     |  |        |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:optional?     boolean
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:transitive?   boolean
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:partial?      boolean
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:extended?     boolean
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:attr-type?    uint8
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:attr-len?     uint16
+       |     |     |     |  |        |        +--ro oc-bgp-evpn-ext:attr-value?   binary
+       |     |     |     |  |        +--ro oc-bgp-evpn-ext:attr-sets
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:origin?             oc-bgpt:bgp-origin-attr-type
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:atomic-aggregate?   boolean
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:next-hop?           oc-inet:ip-address
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:med?                uint32
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:local-pref?         uint32
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:originator-id?      oc-inet:ipv4-address
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:cluster-list*       oc-inet:ipv4-address
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:aigp?               uint64
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:aggregator
+       |     |     |     |  |           |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |           |     +--ro oc-bgp-evpn-ext:as?        oc-inet:as-number
+       |     |     |     |  |           |     +--ro oc-bgp-evpn-ext:as4?       oc-inet:as-number
+       |     |     |     |  |           |     +--ro oc-bgp-evpn-ext:address?   oc-inet:ipv4-address
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:as-path
+       |     |     |     |  |           |  +--ro oc-bgp-evpn-ext:as-segment* []
+       |     |     |     |  |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |  |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:as4-path
+       |     |     |     |  |           |  +--ro oc-bgp-evpn-ext:as4-segment* []
+       |     |     |     |  |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |  |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |  |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:community*          union
+       |     |     |     |  |           +--ro oc-bgp-evpn-ext:ext-community*      oc-bgpt:bgp-ext-community-recv-type
+       |     |     |     |  +--ro oc-bgp-evpn-ext:neighbors
+       |     |     |     |     +--ro oc-bgp-evpn-ext:neighbor* [neighbor-address]
+       |     |     |     |        +--ro oc-bgp-evpn-ext:neighbor-address    -> ../state/neighbor-address
+       |     |     |     |        +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:neighbor-address?   oc-inet:ip-address
+       |     |     |     |        +--ro oc-bgp-evpn-ext:adj-rib-in-pre
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:routes
+       |     |     |     |        |     +--ro oc-bgp-evpn-ext:route* [route-distinguisher prefix]
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:route-distinguisher    -> ../state/route-distinguisher
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:prefix                 -> ../state/prefix
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:prefix?                string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:path-id?               uint32
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:last-modified?         oc-types:timeticks64
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:valid-route?           boolean
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:invalid-reason?        identityref
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:attr-index?            -> ../../../../../../../../../../attr-sets/attr-set/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:community-index?       -> ../../../../../../../../../../communities/community/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:ext-community-index?   -> ../../../../../../../../../../ext-communities/ext-community/state/index
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:unknown-attributes
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:unknown-attribute* [attr-type]
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:attr-type    -> ../state/attr-type
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:optional?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:transitive?   boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:partial?      boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:extended?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-type?    uint8
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-len?     uint16
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-value?   binary
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:attr-sets
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:origin?             oc-bgpt:bgp-origin-attr-type
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:atomic-aggregate?   boolean
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:next-hop?           oc-inet:ip-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:med?                uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:local-pref?         uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:originator-id?      oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:cluster-list*       oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aigp?               uint64
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aggregator
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as?        oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as4?       oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:address?   oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as4-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as4-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:community*          union
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:ext-community*      oc-bgpt:bgp-ext-community-recv-type
+       |     |     |     |        +--ro oc-bgp-evpn-ext:adj-rib-in-post
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:routes
+       |     |     |     |        |     +--ro oc-bgp-evpn-ext:route* [route-distinguisher prefix]
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:route-distinguisher    -> ../state/route-distinguisher
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:prefix                 -> ../state/prefix
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:prefix?                string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:path-id?               uint32
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:last-modified?         oc-types:timeticks64
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:valid-route?           boolean
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:invalid-reason?        identityref
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:best-path?             boolean
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:attr-index?            -> ../../../../../../../../../../attr-sets/attr-set/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:community-index?       -> ../../../../../../../../../../communities/community/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:ext-community-index?   -> ../../../../../../../../../../ext-communities/ext-community/state/index
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:unknown-attributes
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:unknown-attribute* [attr-type]
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:attr-type    -> ../state/attr-type
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:optional?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:transitive?   boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:partial?      boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:extended?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-type?    uint8
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-len?     uint16
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-value?   binary
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:attr-sets
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:origin?             oc-bgpt:bgp-origin-attr-type
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:atomic-aggregate?   boolean
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:next-hop?           oc-inet:ip-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:med?                uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:local-pref?         uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:originator-id?      oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:cluster-list*       oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aigp?               uint64
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aggregator
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as?        oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as4?       oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:address?   oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as4-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as4-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:community*          union
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:ext-community*      oc-bgpt:bgp-ext-community-recv-type
+       |     |     |     |        +--ro oc-bgp-evpn-ext:adj-rib-out-pre
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |  +--ro oc-bgp-evpn-ext:routes
+       |     |     |     |        |     +--ro oc-bgp-evpn-ext:route* [route-distinguisher prefix]
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:route-distinguisher    -> ../state/route-distinguisher
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:prefix                 -> ../state/prefix
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:prefix?                string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:path-id?               uint32
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:last-modified?         oc-types:timeticks64
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:valid-route?           boolean
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:invalid-reason?        identityref
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:attr-index?            -> ../../../../../../../../../../attr-sets/attr-set/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:community-index?       -> ../../../../../../../../../../communities/community/state/index
-       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:ext-community-index?   -> ../../../../../../../../../../ext-communities/ext-community/state/index
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:unknown-attributes
+       |     |     |     |        |        |  +--ro oc-bgp-evpn-ext:unknown-attribute* [attr-type]
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:attr-type    -> ../state/attr-type
+       |     |     |     |        |        |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:optional?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:transitive?   boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:partial?      boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:extended?     boolean
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-type?    uint8
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-len?     uint16
+       |     |     |     |        |        |        +--ro oc-bgp-evpn-ext:attr-value?   binary
+       |     |     |     |        |        +--ro oc-bgp-evpn-ext:attr-sets
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:origin?             oc-bgpt:bgp-origin-attr-type
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:atomic-aggregate?   boolean
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:next-hop?           oc-inet:ip-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:med?                uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:local-pref?         uint32
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:originator-id?      oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:cluster-list*       oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aigp?               uint64
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:aggregator
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as?        oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:as4?       oc-inet:as-number
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:address?   oc-inet:ipv4-address
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:as4-path
+       |     |     |     |        |           |  +--ro oc-bgp-evpn-ext:as4-segment* []
+       |     |     |     |        |           |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |        |           |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:community*          union
+       |     |     |     |        |           +--ro oc-bgp-evpn-ext:ext-community*      oc-bgpt:bgp-ext-community-recv-type
+       |     |     |     |        +--ro oc-bgp-evpn-ext:adj-rib-out-post
+       |     |     |     |           +--ro oc-bgp-evpn-ext:state
+       |     |     |     |           +--ro oc-bgp-evpn-ext:routes
+       |     |     |     |              +--ro oc-bgp-evpn-ext:route* [route-distinguisher prefix]
+       |     |     |     |                 +--ro oc-bgp-evpn-ext:route-distinguisher    -> ../state/route-distinguisher
+       |     |     |     |                 +--ro oc-bgp-evpn-ext:prefix                 -> ../state/prefix
+       |     |     |     |                 +--ro oc-bgp-evpn-ext:state
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:prefix?                string
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:route-distinguisher?   string
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:path-id?               uint32
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:last-modified?         oc-types:timeticks64
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:valid-route?           boolean
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:invalid-reason?        identityref
-       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:attr-index?            -> ../../../../../../../../../../attr-sets/attr-set/state/index
-       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:community-index?       -> ../../../../../../../../../../communities/community/state/index
-       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:ext-community-index?   -> ../../../../../../../../../../ext-communities/ext-community/state/index
+       |     |     |     |                 +--ro oc-bgp-evpn-ext:unknown-attributes
+       |     |     |     |                 |  +--ro oc-bgp-evpn-ext:unknown-attribute* [attr-type]
+       |     |     |     |                 |     +--ro oc-bgp-evpn-ext:attr-type    -> ../state/attr-type
+       |     |     |     |                 |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:optional?     boolean
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:transitive?   boolean
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:partial?      boolean
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:extended?     boolean
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:attr-type?    uint8
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:attr-len?     uint16
+       |     |     |     |                 |        +--ro oc-bgp-evpn-ext:attr-value?   binary
+       |     |     |     |                 +--ro oc-bgp-evpn-ext:attr-sets
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:origin?             oc-bgpt:bgp-origin-attr-type
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:atomic-aggregate?   boolean
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:next-hop?           oc-inet:ip-address
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:med?                uint32
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:local-pref?         uint32
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:originator-id?      oc-inet:ipv4-address
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:cluster-list*       oc-inet:ipv4-address
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:aigp?               uint64
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:aggregator
+       |     |     |     |                    |  +--ro oc-bgp-evpn-ext:state
+       |     |     |     |                    |     +--ro oc-bgp-evpn-ext:as?        oc-inet:as-number
+       |     |     |     |                    |     +--ro oc-bgp-evpn-ext:as4?       oc-inet:as-number
+       |     |     |     |                    |     +--ro oc-bgp-evpn-ext:address?   oc-inet:ipv4-address
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:as-path
+       |     |     |     |                    |  +--ro oc-bgp-evpn-ext:as-segment* []
+       |     |     |     |                    |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |                    |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |                    |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:as4-path
+       |     |     |     |                    |  +--ro oc-bgp-evpn-ext:as4-segment* []
+       |     |     |     |                    |     +--ro oc-bgp-evpn-ext:state
+       |     |     |     |                    |        +--ro oc-bgp-evpn-ext:type?     oc-bgpt:as-path-segment-type
+       |     |     |     |                    |        +--ro oc-bgp-evpn-ext:member*   oc-inet:as-number
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:community*          union
+       |     |     |     |                    +--ro oc-bgp-evpn-ext:ext-community*      oc-bgpt:bgp-ext-community-recv-type

```  

### 3.2.2 CLI  
  
#### 3.2.2.1 Configuration Commands  
  
  
  
#### BGP Global Address-family config mode (for l2vpn-evpn AFI-SAFI) 
  
`sonic(config-router-bgp)# address-family l2vpn evpn `
 
Enters the BGP Global L2VPN-EVPN AFI-SAFI configuration mode  
  
#### Advertise all local VNIs
`sonic(config-router-bgp-af)# advertise-all-vni`
#### Advertise prefix routes
```
sonic(config-router-bgp-af)# advertise 
  ipv4  Address family IPv4
  ipv6  Address family IPv6

sonic(config-router-bgp-af)# advertise ipv4 
  unicast  SAFI unicast

sonic(config-router-bgp-af)#
```
#### Advertise all default gw mac-ip routes in EVPN
`sonic(config-router-bgp-af)# advertise-default-gw`
#### Auto-derivation of route-targets
```
sonic(config-router-bgp-af)# autort 
  rfc8365-compatible  Auto-derivation of RT using RFC8365
sonic(config-router-bgp-af)#
```
#### Originate default route  
```
sonic(config-router-bgp-af)# default-originate 
ipv4 ipv6 
sonic(config-router-bgp-af)#
```
#### Flooding
```
sonic(config-router-bgp-af)# flooding 
  disable               Do not flood any BUM packets
  head-end-replication  Flood BUM packets using head-end replication

sonic(config-router-bgp-af)#
```
#### Duplicate Address Detection
```
sonic(config-router-bgp-af)# dup-addr-detection 
  freeze     Duplicate address detection freeze
  max-moves  Max allowed moves before address detected as duplicate
  <cr>       

sonic(config-router-bgp-af)# dup-addr-detection max-moves 32 
  time  Duplicate address detection time

sonic(config-router-bgp-af)# dup-addr-detection max-moves 32 time 
  Time in seconds 2-1800, default 180  Time in seconds (2..1800)

sonic(config-router-bgp-af)# dup-addr-detection freeze 
  permanent                             Permanent freeze
  Time in seconds 30-3600, default 180   (30..3600)

sonic(config-router-bgp-af)#
```
#### Route distinguisher
```
sonic(config-router-bgp-af)# rd 1.2.3.4:11
```
#### Route-target
```
sonic(config-router-bgp-af)# route-target import 1.2.3.4:11
``` 

#### BGP VNI config mode 

#### configure VNI
```
sonic(config-router-bgp-af)# vni 123 
sonic(config-router-bgp-af-vni)#
```
#### VNI mode: Advertise all default gw mac-ip routes in EVPN
`sonic(config-router-bgp-af-vni)# advertise-default-gw`
#### VNI mode: Route distinguisher
```
sonic(config-router-bgp-af-vni)# rd 1.2.3.4:11
```
#### VNI mode: Route-target
```
sonic(config-router-bgp-af-vni)# route-target import 1.2.3.4:11
``` 
#### 3.2.2.2 Show Commands  
  
#### Display VNI state 
  
`show ip bgp l2vpn evpn vni $vni_number`  
  
```
sonic# show ip bgp l2vpn evpn vni 100
 VNI: 100(known to the kernel)
  Type: L2
  RD: 10.59.142.151:3
  Originator IP: 1.1.1.1
  Mcast group: 0.0.0.0
  Advertise-gw-macip: False
  Import Route Target:
   100:100
  Export Route Target:
   100:100
sonic# 
```
  
#### Display EVPN routes 
  
`show ip bgp l2vpn evpn routes`  
  
```  
sonic# show ip bgp l2vpn evpn routes 
BGP table version is 1, local router ID is 
Status codes: s suppressed, d damped, h history, * valid, > best, i - internal
Origin codes: i - IGP, e - EGP, ? - incomplete
EVPN type-1 prefix: [1]:[ESI]:[EthTag]
EVPN type-2 prefix: [2]:[EthTag]:[MAClen]:[MAC]:[IPlen]:[IP]
EVPN type-3 prefix: [3]:[EthTag]:[IPlen]:[OrigIP]
EVPN type-4 prefix: [4]:[ESI]:[IPlen]:[OrigIP]
EVPN type-5 prefix: [5]:[EthTag]:[IPlen]:[IP]
 
     Network             Next Hop            Metric  LocPref Weight  Path           
                         Extended Community  
Route Distinguisher: 10.59.142.151:3
*    [3]:[0]:[32]:[1.1.1.1]
                         1.1.1.1                             0       0 ?
Route Distinguisher: 10.59.142.183:2
*    [3]:[0]:[32]:[2.2.2.2]
                         2.2.2.2                             0       0 ?
sonic# 
 
```  
  
### 3.2.3 REST API Support  
  
All config and show commands
  
## 3.3 DB Changes  
This section describes the changes made to different DB's for supporting BGP EVPN.  
### 3.3.1 CONFIG DB  
  
New tables and keys are defined to maintain BGP EVPN configuration in configDB.  
```diff
  +--rw sonic-bgp-global
     ...
     +--rw BGP_GLOBALS_AF
     |  +--rw BGP_GLOBALS_AF_LIST* [vrf_name afi_safi]
     ...
     |     +--rw advertise-default-gw?        boolean
     |     +--rw route-distinguisher?         string
     |     +--rw advertise-all-vni?           boolean
     |     +--rw advertise-ipv4-unicast?      boolean
     |     +--rw advertise-ipv6-unicast?      boolean
     |     +--rw default-originate-ipv4?      boolean
     |     +--rw default-originate-ipv6?      boolean
     |     +--rw autort?                      string
     |     +--rw flooding?                    string
     |     +--rw dad-enabled?                 boolean
     |     +--rw dad-max-moves?               uint32
     |     +--rw dad-time?                    uint32
     |     +--rw dad-freeze?                  string
     ...
     +--rw BGP_GLOBALS_EVPN_RT
     |  +--rw BGP_GLOBALS_EVPN_RT_LIST* [vrf afi-safi-name route-target]
     |     +--rw vrf                  string
     |     +--rw afi-safi-name        string
     |     +--rw route-target         string
     |     +--rw route-target-type?   string
     +--rw BGP_GLOBALS_EVPN_VNI
     |  +--rw BGP_GLOBALS_EVPN_VNI_LIST* [vrf afi-safi-name vni-number]
     |     +--rw vrf                     string
     |     +--rw afi-safi-name           string
     |     +--rw vni-number              uint32
     |     +--rw advertise-default-gw?   boolean
     |     +--rw route-distinguisher?    string
     +--rw BGP_GLOBALS_EVPN_VNI_RT
        +--rw BGP_GLOBALS_EVPN_VNI_RT_LIST* [vrf afi-safi-name vni-number route-target]
           +--rw vrf                  string
           +--rw afi-safi-name        string
           +--rw vni-number           uint32
           +--rw route-target         string
           +--rw route-target-type?   string

```
# 4 Flow Diagrams  
  
N/A  
  
  
  
# 5 Error Handling  
  
N/A  
  
  
  
# 6 Serviceability and Debug  
  
N/A  
  
  
  
# 7 Warm Boot Support  
  
N/A  
  
  
  
# 8 Scalability  
  
N/A  
  
  
  
# 9 Unit Test  
  
#### Configuration and Show via CLI/REST 
  
  
  
|**Test-Case ID**|**Test Scenario**|  
  
|----------------|-----------------|  
  
1| Verify BGP AFI-SAFI config for L2VPN-EVPN.  
  
2| Verify advertise-all-vni config for global AF.  
  
3| Verify advertise [afi-safi] config for global AF.  
  
4| Verify advertise default gateway config for global AF.
  
5| Verify autort config  for global AF.
  
6| Verify default-originate config for global AF.  
  
7| Verify duplicate address detection config for global AF.  
  
8| Verify duplicate address detection parameters for global AF. 
  
9| Verify duplicate address detection freeze parameters for global AF.  
  
10| Verify flooding parameters config for global AF  
  
11| Verify route distinguisher config for global AF  
  
12| Verify route-target config for global AF 
  
13| Verify VNI config under global AF  
  
14| Verify advertise default gw config for VNI.  
  
15| Verify route distinguisher config for VNI.  
  
16| Verify route-target config for global for VNI.  
  
17| Verify specific VNI display

18| Verify EVPN routes display

19| Verify EVPN routes display filters
  
#### Configuration via gNMI  
  
  
  
Same as CLI configuration test, but using gNMI SET request  
  
  
  
#### Get configuration via gNMI  
  
  
  
Same as CLI show test, but using gNMI GET request, verify the JSON response.  
  
  
  
#### Configuration via REST (PATCH)  
  
  
  
Same as CLI configuration test, but using REST request  
  
  
  
#### Get configuration via REST (GET)  
  
  
  
Same as CLI show test, but using REST GET request, verify the JSON response.  
  
  
  
# 10 Internal Design Information  
  
N/A
