<!-- omit in toc -->
# SONiC SRv6 Policy HLD
<!-- omit in toc -->
# Revision
| Rev  |    Date    |       Author        | Change Description                                           |
|:--:|:--------:|:-----------------:|:------------------------------------------------------------:|
| 1.0  | Jun 2024 |   Eddie Ruan (Alibaba) | Initial version

<!-- omit in toc -->
# Table of Context
- [Overview](#overview)
  - [SONiC SRv6 Policy's prerequisites](#sonic-srv6-policys-prerequisites)
- [SRv6 Policy Configuration](#srv6-policy-configuration)
  - [FRR SRv6 Policy Configuration](#frr-srv6-policy-configuration)
    - [FRR Sample Configuration](#frr-sample-configuration)
  - [SONiC Policy Configuration](#sonic-policy-configuration)
    - [SRV6\_POLICY's CONFIGDB schema](#srv6_policys-configdb-schema)
    - [RV6\_SID\_LIST's CONFIGDB schema](#rv6_sid_lists-configdb-schema)
- [SRv6 Policy Related APPDB Schemas](#srv6-policy-related-appdb-schemas)
  - [Route Schema](#route-schema)
  - [PIC Contexts schema](#pic-contexts-schema)
  - [Forwarding information NHG's schema](#forwarding-information-nhgs-schema)
  - [SID LIST Schema](#sid-list-schema)
- [Candidate-path management](#candidate-path-management)
  - [SID\_LIST paths from pathd to oarchagent](#sid_list-paths-from-pathd-to-oarchagent)
- [SRv6 Policy Handling Work Flows in Zebra](#srv6-policy-handling-work-flows-in-zebra)
  - [SRv6 Policy Configuration Handling Work Flow](#srv6-policy-configuration-handling-work-flow)
    - [zread\_srv6\_policy\_set](#zread_srv6_policy_set)
    - [zread\_srv6\_policy\_delete](#zread_srv6_policy_delete)
  - [Policy NH register work flow](#policy-nh-register-work-flow)
    - [Remote PE Announce routes with color](#remote-pe-announce-routes-with-color)
    - [local PE register RNH](#local-pe-register-rnh)
  - [BGP resolve routes via SRv6 Policies](#bgp-resolve-routes-via-srv6-policies)
    - [PIC Context](#pic-context)
    - [Policy NHG](#policy-nhg)
    - [zebra sends SRv6 Policy to fpm](#zebra-sends-srv6-policy-to-fpm)
- [Orchagent changes for SRv6 Policy](#orchagent-changes-for-srv6-policy)
- [Unit Test](#unit-test)

# Overview
The purpose of using SRv6 Policy is to provide a mechanism to steer different types of service traffic via different paths within the SRv6-based backbone network. Each policy is identified by a combination of a color and an endpoint address. The color can be used as a service indicator. The endpoint address could represent a remote PE address or a prefix. A special case is the color only case, which implicitly means that the endpoint address is "::/0". Each policy could contain a set of candidate paths. Unlike the current FRR MPLS TE approach, we allow multiple candidate paths with the same preferences and each candidate path is determined by a given sidlist. This allows us to adopt multiple ECMP paths to reach a remote PE under one given policy. Since BGP routes are learned through multiple PEs, we can have a set of policies used by BGP routes. The relationship between routes and policies is illustrated in the following diagram.

<figure align=center>
    <img src="images/srv6_policy_and_cpath.jpg" width="600" height="400" >
    <figcaption>Figure 1. SRv6 Policy <br><br><figcaption>
</figure>

Current FRR code base has already handled traffic engineering policies for MPLS segments. This HLD outlines the modifications needed to utilize the existing FRR traffic engineering policy infrastructure for managing SRv6 Policies.

## SONiC SRv6 Policy's prerequisites
SRv6 Policy requires the following features / enhancements in SONiC deployments.

1. NHG ID handling. NHG ID handlding is required by the policy updating approach.
2. Prefix Independent Convergence (PIC). PIC is for improveing VPN routes' routes convergence. 
3. SONiC fpm module. That is required for supporting features/enhancements not supported in current Linux kernel.

# SRv6 Policy Configuration
## FRR SRv6 Policy Configuration
FRR has existing traffic engineering policy configurations in segment-routing configuration block. We extend current policy infrastructure to fit SRv6 Policy's requirements. There are three main enhancements from existing TE configurations.
1. Add "ipv6-address" as segment type for segment list for SRv6. Currently, it only has "mpls" and "nai" as segment type.
2. Add BFD protection to each segment list in policy. 
3. As shown in the above diagram, allow multiple candidate-paths to have the same preference within one policy. Current FRR assumes only one candidate-path at each preference within one policy.

### FRR Sample Configuration
```
segment-routing
 traffic-eng
  segment-list a
   index 1 ipv6-address fd00:205:205:fff5:55::
  exit
  segment-list b
   index 2 ipv6-address fd00:206:206:fff6:66::
  exit
  segment-list c
   index 3 ipv6-address fd00:207:207:fff7:77::
  exit
  segment-list d
   index 4 ipv6-address fd00:204:204:fff4:44::
  exit
  policy color 1 endpoint 2064:100::1d
   candidate-path preference 1 name a explicit segment-list a weight 1 bfd-name test3
   candidate-path preference 1 name b explicit segment-list b weight 1 bfd-name test4
  exit
  policy color 3 endpoint 2064:100::1e
   candidate-path preference 1 name c explicit segment-list c weight 1 bfd-name test2
   candidate-path preference 1 name d explicit segment-list d weight 1 bfd-name test1
  exit
 exit
 srv6
exit
end
```
## SONiC Policy Configuration
We want to introduce two new configurations in SONiC, SRV6_POLICY and SRV6_SID_LIST.

### SRV6_POLICY's CONFIGDB schema
```
; New table
; holds SRv6 policy

key = SRV6_POLICY|<color>|<v6_address>

; field = value
cpaths = 4-tuples,   ; List of 4 tuples

4-tuples = <preference>|<cpath name>|<sid list name>|<weight>

For example:

    "SRV6_POLICY": {
        "1|2064:100::1d":{
            "cpath":[
                "1|a|a|1",
                "1|b|b|1"
            ]
        },
        "3|2064:100::1e":{
            "cpath":[
                "1|c|c|1",
                "1|d|d|1"
            ]
        }
    },
```

### RV6_SID_LIST's CONFIGDB schema
```
; New table
; holds SRV6_SID_LIST

key = SRV6_SID_LIST|<sid_list_name>

; field = value
<sid list name> = ip address,   ; List of segment addresses

For example:

    "SRV6_SID_LIST": {
        "a": {
            "1": "fd00:205:205:fff5:55::"
        },
        "b": {
            "2": "fd00:206:206:fff6:66::"
        },
        "c": {
            "3": "fd00:207:207:fff7:77::"
        },
        "d": {
            "4": "fd00:204:204:fff4:44::"
        }
    },
```

# SRv6 Policy Related APPDB Schemas
The following is an example of VPNv4 route going via two SRv6 policies, one policy is color 1 via remote PE 2064:100::1d and the other policy is coloar 3 via remote PE 2064:100::1e.

```
show ip route vrf PUBLIC-TC11 192.100.1.9/32 nexthop-group  
Routing entry for 192.100.1.9/32
  Known via "bgp", distance 20, metric 0, vrf PUBLIC-TC11, best
  Last update 08:44:23 ago
  Nexthop Group ID: 8661
  PIC Context ID: 8657
  * 2064:100::1d segment-list (vrf Default), label implicit-null, seg6local unspec unknown(seg6local_context2str), seg6 fd00:201:201:fff1:11::, weight 1, srv6tunnel(endpoint|color):2064:100::1d|1
  * 2064:100::1e segment-list (vrf Default), label implicit-null, seg6local unspec unknown(seg6local_context2str), seg6 fd00:202:202:fff2:22::, weight 1, srv6tunnel(endpoint|color):2064:100::1e|3
```

## Route Schema
VPN Route uses the existing route netlink format with pic_context_id is added in TLV. In the example above, VPNv4 route points NHG with id  8661 for forwarding information and 8657 for PIC context, a.k.a VPN SID information.
```
127.0.0.1:6380> hgetall "ROUTE_TABLE:Vrf10000:192.100.1.9/32"
 1) "nexthop_group"
 2) "8661"
 3) "pic_context_id"
 4) "8657"
 5) "nexthop"
 6) "na"
 7) "ifname"
 8) "na"
 9) "vni_label"
1)  "na"
2)  "vpn_sid"
3)  "na"
4)  "segment"
5)  "na"
6)  "seg_src"
7)  "na"
8)  "blackhole"
9)  "false"
```

## PIC Contexts schema
PIC context is mapped from a NHG in zebra by fpmsyncd during NHG handling. The main purpose for this NHG is for provide VPN sid needed after reaching remote PE. 
```
ARISTA03T1# show nexthop-group rib  8657    
ID: 8657 (zebra 0x562eba98bb00)
     RefCnt: 0
     segment_ref: 10
     Uptime: 08:48:11
     VRF: Default
     Falgs: 0x403
     Valid, Installed
     SegDepends: (8583) (8658)
           via 2064:100::1d segment-list  color 1 (vrf Default), label implicit-null, seg6local unspec unknown(seg6local_context2str), seg6 fd00:201:201:fff1:11::, weight 1
           via 2064:100::1e segment-list  color 3 (vrf Default), label implicit-null, seg6local unspec unknown(seg6local_context2str), seg6 fd00:202:202:fff2:22::, weight 1
     pic nhe:8661 
```

This PIC NHG would create an entry in APPDB's PIC_CONTEXT_TABLE. The schema is the similar to current NEXTHOP_GROUP_TABLE's schema.
```
127.0.0.1:6380> hgetall "PIC_CONTEXT_TABLE:8657"
1) "nexthop"
2) "2064:100::1d,2064:100::1e"
3) "vni_label"
4) "na,na"
5) "vpn_sid"
6) "fd00:201:201:fff1:11::,fd00:202:202:fff2:22::"
7) "seg_src"
8) "2064:100::1f,2064:100::1f"
```

## Forwarding information NHG's schema
Zebra maintains a SRv6 Policy NHG in two levels. The first level is ECMP over multiple polices, and the second level is ECMP over multiple candidate paths. 
```
show nexthop-group rib  8661
ID: 8661 (zebra 0x562eba5d0610)
     RefCnt: 0
     segment_ref: 1
     Uptime: 09:11:19
     VRF: Default
     Falgs: 0x503
     Valid, Installed
     This is a pic nhe.
     SegDepends: (8584) (8659)
        via 2064:100::1d segment-list  color 1 (vrf Default) (recursive), weight 1
           via 2064:100::1d segment-list a color 1 (vrf Default), weight 1
           via 2064:100::1d segment-list b color 1 (vrf Default), weight 1
        via 2064:100::1e segment-list  color 3 (vrf Default) (recursive), weight 1
           via 2064:100::1e segment-list d color 3 (vrf Default), weight 1

```

Zebra collapses these two levels into one level which would be described below. The NHG inforamtion would be stored in NEXTHOP_GROUP_TABLE in appdb. Two new fields are added, segment's names and weights. Segment name would be used to find out SID_LIST created from pathd, which would build up SRv6 NH with SID LIST binding in SAI layer. 

```
; Modify table
; holds NEXTHOP_GROUP_TABLE

key = NEXTHOP_GROUP_TABLE|<nhgid>

; field = value
segment =  <seg name>,   ; List of segment names
weight =  <weight>,   ; List of segment weights


For example:

127.0.0.1:6380> hgetall "NEXTHOP_GROUP_TABLE:8661"
 1) "nexthop"
 2) "2064:100::1d,2064:100::1d,2064:100::1e"
 3) "ifname"
 4) "unknown,unknown,unknown"
 5) "vni_label"
 6) "na,na,na"
 7) "vpn_sid"
 8) "::,::,::"
 9) "seg_src"
1)  "2064:100::1f,2064:100::1f,2064:100::1f"
2)  "segment"
3)  "a,b,d"
4)  "weight"
5)  "1,1,1"
```

## SID LIST Schema
SID LIST would be populated from pathd. This schema provides detail path information for each candidate path, a.k.a SID LIST.

Here is a sample example for SID_LIST in appdb. The schema is defined in the previous section. 
```
; New table
; holds SRV6_SID_LIST_TABLE

key = SRV6_SID_LIST_TABLE|<sid_list_name>

; field = value
path= ip addresses,   ; List of segment addresses, seperated via ,

For example:

127.0.0.1:6380> keys *SID_LIST*
1) "SRV6_SID_LIST_TABLE:b"
2) "SRV6_SID_LIST_TABLE:d"
3) "SRV6_SID_LIST_TABLE:a"
4) "SRV6_SID_LIST_TABLE:c"
127.0.0.1:6380> hgetall "SRV6_SID_LIST_TABLE:a"
1) "path"
2) "fd00:205:205:fff5:55::"
127.0.0.1:6380> 
```

# Candidate-path management
Similar to MPLS SR case, Pathd is responsible to maintain each candidate path's status. BFD protection for candidate paths would be discussed in a separate HLD.  From zebra point of view, it would get ZEBRA_SRV6_POLICY_SET message from pathd whenever a new policy is applied or some policy information is updated and it would get ZEBRA_SRV6_POLICY_DELETE message from pathd whenever there is a policy is deleted.

## SID_LIST paths from pathd to oarchagent
The overall workflow is the following
1. Pathd loads new sonic fpm lib and use TLV to pass SID_LIST to fpmsyncd. 
2. fpmsyncd picks message from fpm socket and  store sid list in SRV6_SID_LIST_TABLE in appdb. 
3. Orchagent picks SID_LIST data from appdb. SID list would be programmed to SIDLIST table via SAI api directly. When NH with segment name comes in orchagent, orchagent will retrieve SIDLIST's OID and set it in NH's SAI object. 

# SRv6 Policy Handling Work Flows in Zebra
Zebra has the following SRv6 Policy related work flows, which are shown in the following diagram. 

1. SRv6 Policy Configuration handling Work Flow
2. Policy NH register work flow
3. Roues handling work flow

<figure align=center>
    <img src="images/srv6_policy_workflows.jpg " width="600" height="400"  >
    <figcaption>Figure 2. SRv6 Policy related work flows <br><br><figcaption>
</figure>

The following subsections would describe the changes needed for each work flow.

## SRv6 Policy Configuration Handling Work Flow
MPLS segment Policy is handled via the following two handlers in zapi_msg.c
```
	[ZEBRA_SR_POLICY_SET] = zread_sr_policy_set,
	[ZEBRA_SR_POLICY_DELETE] = zread_sr_policy_delete,
```
We would like to add the following two more handlers in zapi_msg.c for SRv6 Policies' handling.
```
	[ZEBRA_SRV6_POLICY_SET] = zread_srv6_policy_set,
	[ZEBRA_SRV6_POLICY_DELETE] = zread_srv6_policy_delete,
```

zread_srv6_policy_set() and zread_srv6_policy_delete() would be responsible for handling SRv6 policy create, update or delete events. These events could be triggered by pathd's messages based on polices, which includes cpath UP, DOWN events, cpath sid list update events. 

### zread_srv6_policy_set
The policy set handling work flow is shown in the following diagram. The overall logic for zread_srv6_policy_set() is similar to MPLS SR's zread_sr_policy_set()'s handling.

<figure align=center>
    <img src="images/srv6_policy_set_workflow.jpg" width="600" height="600" >
    <figcaption>Figure 3. SRv6 Policy Set work flow <br><br><figcaption>
</figure>

1. zread_srv6_policy_set parses the following structure from the incoming message. The message format reuses struct zapi_sr_policy with new SRv6 policy specific fields included. 

2.  Then it reuses the following api struct zebra_sr_policy *zebra_sr_policy_add_by_prefix(struct prefix *p, uint32_t color, char *name) to create struct zebra_sr_policy and store it in srte_table_hash hash table which uses color and prefix as the hash key. This is a common part which reuses existing srte_hash_table infra.

3. zebra_srv6_policy_validate() : If it is a new policy, it would trigger zebra_srte_evaluate_rn_nexthops(), otherwise it would trigger zebra_nhe_seg_update() to update all NHGs using this this policy. zebra_nhe_seg_update() wouldate trigger related NHGs getting updates in data plane.

4. zebra_srte_evaluate_rn_nexthops() : trigger update rnh which is associated with policies. RNH could be registered before policy is created. When that happens, the RNH would be registered with rn node which could cover it. Normally this rn node is for ::/0. zebra_srte_evaluate_rn_nexthops()  would walk through rn nodes and pick up these rnhs belong to the given policy.

5. zebra_evaluate_rnh_by_srte(): a wrapper function for zebra_rnh_eval_nexthop_entry_srte()

6. zebra_rnh_eval_nexthop_entry_srte() : This function checks if the policy state via the given rnh is updated. If so, it would use zebra_rnh_store_in_srte_table() to update policy's rnh list. 

7. zebra_sr_policy_notify_update() : This is an existing function in FRR, which would be responsible to inform corresponding zebra client on updating policy's rnh event. 

### zread_srv6_policy_delete
If policy is still in UP state, the poligy would be deactive first. Then the created policy structures would be cleaned up. 

## Policy NH register work flow
### Remote PE Announce routes with color
Remote PE could announce VPN routes with color, which could be used as a service indication. In the following sample configuration, all vrf PUBLIC-TC11's v4 routes would be marked with color 1 via export route-map sr1. These color marking codes are existing FRR codes, there is no specific changes for SRv6 policy.

```
router bgp 64600 vrf PUBLIC-TC11
 bgp router-id 100.1.0.29
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 bgp bestpath as-path multipath-relax
 timers bgp 10 30
 neighbor 10.10.246.254 remote-as 64600
 neighbor 10.10.246.254 description exabgp_v4
 neighbor 10.10.246.254 solo
 neighbor 10.10.246.254 advertisement-interval 0
 srv6-locator lsid1
 !
 address-family ipv4 unicast
  neighbor 10.10.246.254 activate
  neighbor 10.10.246.254 soft-reconfiguration inbound
  maximum-paths 64
  rd vpn export 2:2
  rt vpn both 1:1
  route-map vpn export sr1
  export vpn
  import vpn
 exit-address-family
exit
!
!
route-map sr1 permit 10
 set extcommunity color 1
exit
!

```

### local PE register RNH
After BGP receives routes from the remote peer, bgpd will receive bgp path information and register needed NH information with zebra via ZEBRA_NEXTHOP_REGISTER message. This message would carry color in addtional to nexthop information. NEXTHOP_REGISTER_TYPE_COLOR is used as type for carrying color in user data. This part is a common piece. 

## BGP resolve routes via SRv6 Policies
THe nexthops provided with BGP routes contains both colors and nexthop addresses when policy is in use. Each pair of color and nexthop address could be used to identify a specific policy. This set of policies forms a NHG, which each NH in this NHG represents a policy. The policy would also be resolved via a set of NHs, which each NH represents a candidate path, a.k.a sid list. 

### PIC Context
PIC context contains vpn SID only. Candidate path's NH is referred via forwarding NHG only. The real SID LIST is not part of NH. We only need a segment name as a reference in NH. From the high level, PIC's handling is independent to SRv6 policy.

### Policy NHG
Each policy would be mapped to a NHG, with each NH for SIDLIST. We will introduce a new util function to convert a policy to a NHG. During ROUTE_ADD event, zebra will base on the incoming routes' next hop information to form a recursive NHG over mulitple policy NHGs.
   
### zebra sends SRv6 Policy to fpm
Since there are two levels NHGs, we would like to collapse them to be one level before sending to fpm.  For this purpose, we create a util function with the following signiture in the API. This util function coverts a NHG for a list of SRv6 policies to a list nhg structure. 

```
/* Convert a nhe into a group array */
uint8_t zebra_nhg_seg_nhe2grp(struct nh_grp *grp, struct nhg_hash_entry *nhe,
			  int max_num)
```

This util function would walk through nhe's dependent list and put all cpaths into one arrays. Each struct nh_grp contains to a cpath NH id with associated weight.

```
struct nh_grp {
	uint32_t id;
	uint8_t weight;
};
```
segment name would be used to represent each path's out going information.

# Orchagent changes for SRv6 Policy
Orchagent add new codes for SID_LIST add, modify and delete event. We have segment list and weight list in NHG event. Orchagent would be responsible to look up for created SID_LIST OID based on segment names.

# Unit Test
The unit test would be carried in the 7 nodes test topology and would be committed to sonic-mgmt repro. The detail test plan would be created in a separate testing HLD.
<figure align=center>
    <img src="images/ptf_7node_testbed.jpg" width="600" height="400" >
    <figcaption>Figure 3. SRv6 Policy Set work flow <br><br><figcaption>
</figure>






