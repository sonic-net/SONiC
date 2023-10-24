<!-- omit in toc -->
# BGP PIC HLD
<!-- omit in toc -->
### Revision
| Rev |     Date    |       Author           | Change Description                |
|:---:|:-----------:|:----------------------:|-----------------------------------|
| 0.1 | Oct  8 2023 |   Eddie Ruan / Lingyu Zhang   | Initial Draft              |

<!-- omit in toc -->
## Table of Content
- [Goal and Scope](#goal-and-scope)
- [High Level Design](#high-level-design)
- [Zebra's Data Structure Modifications](#zebras-data-structure-modifications)
  - [Exiting Struct nexthop](#exiting-struct-nexthop)
  - [Updated data structure with BGP PIC changes](#updated-data-structure-with-bgp-pic-changes)
  - [struct nhg\_hash\_entry](#struct-nhg_hash_entry)
  - [struct dplane\_route\_info](#struct-dplane_route_info)
  - [struct dplane\_neigh\_info](#struct-dplane_neigh_info)
- [Zebra Modifications](#zebra-modifications)
  - [BGP\_PIC enable flag](#bgp_pic-enable-flag)
  - [Create pic\_nhe](#create-pic_nhe)
  - [Handles kernel forwarding objects](#handles-kernel-forwarding-objects)
  - [Handles FPM forwarding objects](#handles-fpm-forwarding-objects)
    - [Map Zebra objects to APP\_DB via FPM](#map-zebra-objects-to-app_db-via-fpm)
    - [How would pic\_nhg improve BGP convergence](#how-would-pic_nhg-improve-bgp-convergence)
    - [SRv6 VPN SAI Objects](#srv6-vpn-sai-objects)
    - [Map APP\_DB to SAI objects](#map-app_db-to-sai-objects)
  - [Orchagent Modifications](#orchagent-modifications)
- [Zebra handles NHG member down events](#zebra-handles-nhg-member-down-events)
  - [Local link down events](#local-link-down-events)
  - [BGP NH down events](#bgp-nh-down-events)
- [Unit Test](#unit-test)
  - [FRR Topotest](#frr-topotest)
  - [SONiC mgmt test](#sonic-mgmt-test)
- [References](#references)

## Goal and Scope
BGP PIC, as detailed in the RFC available at https://datatracker.ietf.org/doc/draft-ietf-rtgwg-bgp-pic/, addresses the enhancement of BGP route convergence. This document outlines a method to arrange forwarding structures that can lead to improved BGP route convergence. BGP PIC offers two primary enhancements:

- It prevents BGP load balancing updates from being triggered by IGP load balancing updates. This issue, which is discussed in the SONiC Routing Working Group (https://lists.sonicfoundation.dev/g/sonic-wg-routing/files/SRv6%20use%20case%20-%20Routing%20WG.pptx), can be effectively resolved using BGP PIC.

<figure align=center>
    <img src="images/srv6_igp2bgp.jpg" >
    <figcaption>Figure 1. Alibaba issue Underlay routes flap affecting Overlay SRv6 routes <figcaption>
</figure> 

**Note:** <span style="color:yellow"> We only handle VPN overlay routes via BGP PIC in this HLD. For global table's recursive routes handling, it would be handled via an incoming HLD which would be led by Accton team. </span>

-  We aim to achieve fast convergence in the event of a hardware forwarding failure related to a remote BGP PE becoming unreachable. Convergence in the slow path forwarding mode is not a priority.
<figure align=center>
    <img src="images/pic.png" >
    <figcaption>Figure 2. BGP PIC for improving remote BGP PE down event handling <figcaption>
</figure> 


  -  The provided graph illustrates that the BGP route 1.1.1.1 is advertised by both PE2 and PE3 to PE1. Each BGP route update message not only conveys the BGP next-hop information but also includes VPN context details. 
  -  Consequently, when forming BGP Equal-Cost Multipath (ECMP) data structures, it is natural to retain both the BGP next-hop data and context information for each path. The VPN context could be specific to each prefix (a.k.a per prefix), individual customer edge (a.k.a per CE), or Virtual Routing and Forwarding (per VRF) type. This often leads to situations where BGP ECMP data structures cannot be effectively shared, as indicated in the lower-left section of the diagram. When a remote PE goes offline, PE1 must update all relevant BGP ECMP data structures, which can involve handling prefixes of varying lengths, resulting in an operation with a time complexity of O(N). 

   - The concept of the Prefix Independent Convergence's (PIC) proposal is to restructure this information by segregating the BGP next-hop information from the VPN context. The BGP next-hop-only information will constitute a new BGP ECMP structure that can be shared among all associated BGP VPN routes, as depicted in the lower-right part of the diagram. This approach allows for more efficient updates when the Interior Gateway Protocol (IGP) detects a BGP next-hop failure, resulting in an operation with a time complexity of O(1). This strategy aims to minimize traffic disruption in the hardware. The VPN context will be updated once BGP routes have reconverged.

## High Level Design
One of the challenges in implementing PIC within FRR is the absence of PIC support in the Linux kernel. To minimize alterations in FRR while enabling PIC on platforms that do not require Linux kernel support for this feature, we are primarily focused on two key modifications:
1. In the 'zebra' component:
    - Introduce a new Next Hop Group (PIC-NHG) specifically for the FORWARDING function. This NHG will serve as the shareable NHG in hardware.
    - When a BGP next hop becomes unavailable, zebra will first update the new FORWARDING-ONLY NHG before BGP convergence takes place.
    - When IGP updates, zebra will check associated BGP NHs' reachabilities. If the reachability of each individual member within the BGP NHG is not changed, there is no need to update the BGP NHG.
    - Zebra will transmit two new forwarding objects, BGP PIC context, and NHG, to orchagent via FPM. The handling of NHG is outlined in https://github.com/sonic-net/SONiC/pull/1425.
    - Zebra will continue to update kernel routes in the same manner as before, as the kernel does not support BGP PIC.
2. In the orchagent component:
    - Orchagent will be responsible for managing the two new forwarding objects, BGP PIC context, and NHG.

## Zebra's Data Structure Modifications
### Exiting Struct nexthop
The existing zebra nexthop structure encompasses both FORWARDING details and certain route CONTEXT information, such as VNI (Virtual Network Identifier) and srv6_nh, for various VPN (Virtual Private Network) functionalities. Given that route CONTEXT may vary among different VPN routes, it is not feasible for VPN routes to share the current VPN nexthop group generated by the zebra nexthop structure. When a remote BGP peer becomes inactive, zebra is required to update all linked VPN nexthop groups, potentially involving a significant number of VPN routes.

struct nexthop {

        struct nexthop *next;
        struct nexthop *prev;
        /*
         * What vrf is this nexthop associated with?
         */                
        vrf_id_t vrf_id;
        /* Interface index. */
        ifindex_t ifindex;

        enum nexthop_types_t type;

        uint16_t flags;

        /* Nexthop address */
        union {
                union g_addr gate; 
                enum blackhole_type bh_type;
        };
        union g_addr src;

        ...

        /* Encapsulation information. */
        enum nh_encap_type nh_encap_type;
        union {
                vni_t vni;
        } nh_encap;
        /* EVPN router's MAC.
         * Don't support multiple RMAC from the same VTEP yet, so it's not
         * included in hash key.
         */
        struct ethaddr rmac;
        /* SR-TE color used for matching SR-TE policies */
        uint32_t srte_color;
        /* SRv6 information */
        struct nexthop_srv6 *nh_srv6;
};

The forwarding objects in zebra are organized as the following mannar. Each struct nexthop contains forwarding only part and route context part. Due to route context parts are route attributes, they may be different for different routes. Therefore, struct nexthop_group may not be sharable. 
<figure align=center>
    <img src="images/zebra_fwding_obj_no_share.jpg" >
    <figcaption>Figure 3. Existing Zebra forwarding objects <figcaption>
</figure> 

### Updated data structure with BGP PIC changes
Instead of dividing the current 'struct nexthop' into two separate structures, we have opted to utilize the same nexthop structure to store both the route context part (also known as PIC CONTEXT) and the forwarding part.

Within the 'struct nhg_hash_entry,' we introduce a new field, 'struct nhg_hash_entry *pic_nhe.' This 'pic_nhe' is created when the original NHG pertains to BGP PIC. 'pic_nhe' points to an NHG that exclusively contains the original nexthop's forwarding part. The original nexthop retains both the PIC CONTEXT part and the forwarding part.

This approach allows us to achieve the following objectives:
- Utilize existing code for managing nexthop dependencies.
- Maintain a consistent approach for dplane to handle updates to the Linux kernel.

The new forwarding chain will be organized as follows.
<figure align=center>
    <img src="images/zebra_fwding_obj_sharing.jpg" >
    <figcaption>Figure 4. Zebra forwarding objects after enabling BGP PIC <figcaption>
</figure> 

### struct nhg_hash_entry 
As described in the previous section, we will add a new field struct nhg_hash_entry *pic_nhe in struct nhg_hash_entry.
If PIC NHE is not used, pic_nhe would be set to NULL.

### struct dplane_route_info
dplane_route_info is in struct zebra_dplane_ctx 

We will add two new fields, zd_pic_nhg_id , zd_pic_ng. zd_pic_nhg_id is for pic_nhg's nh id, zd_pic_ng stores pic_nhg.  These two new fields would be collected via dplane_ctx_route_init().

		/* Nexthops */
	uint32_t zd_nhg_id;
	struct nexthop_group zd_ng;
        /* PIC Nexthops */
    uint32_t zd_pic_nhg_id;
	struct nexthop_group zd_pic_ng;

 These fields would be used in the following manner.

| Cases |    Linux Kernel Update (slow path)   |      FPM (fast path)          |
|:-----:|:------------------------------------:|:-----------------------------:|
| No BGP PIC enabled | zd_ng is used as NHG  |    zd_ng is used as NHG |
| BGP PIC enabled | zd_ng is used as NHG | zd_ng is used for PIC_CONTEXT, zd_pic_ng is used for NHG |

### struct dplane_neigh_info
This stucture is initialized via dplane_ctx_nexthop_init(), which is used to trigger NHG events. We don't need to make changes in this structure.

## Zebra Modifications
### BGP_PIC enable flag
BGP_PIC_enable flag would be set based on zebra's command line arguments. This flag would be set only on the platform which Linux kernel supports NHG, a.k.a kernel_nexthops_supported() returns true.

### Create pic_nhe
From dplane_nexthop_add(), when normal NHG is created, we will try to create PIC NHG as well.
zebra_nhe_find() is used to create or find a NHE. In create case, when NHE is for BGP PIC and BGP_PIC is enabled, we use the same same API to create a pic_nhe, a.ka. create nexthop with FORWARDING information only. The created pic_nhe would be stored in the new added field struct nhg_hash_entry *pic_nhe.

### Handles kernel forwarding objects
There is no change for zebra to handle kernel forwarding objects. Only zg_ng is used for NHG programming in kernel. 

### Handles FPM forwarding objects
#### Map Zebra objects to APP_DB via FPM
When BGP_PIC is enabled, nhe's NHG would map to PIC_LIST, pic_nhe's NHG would map to forwarding NHG.
Route object would use nhe's id as context id and use pic_nhe's id as NHG id.

<figure align=center>
    <img src="images/zebra_map_to_fpm_objs.jpg" >
    <figcaption>Figure 5. Zebra maps forwarding objects to APP DB Objs when BGP PIC enables.<figcaption>
</figure> 

The following talbe compares the number of forwarding objects created with and without PIC enabled. N is the number of VPN routes and assume all N VPN routes share the same forwarding only part which makes the discussion easy. 
| Forwarding Objects | No BGP PIC enabled | BGP PIC enabled |
|:-----:|:------------------------------------:|:-----------------------------:|
| Route |  N  | N |
| NHG   |  N  | 1 |
| CONTEXT | n/a | N |

#### How would pic_nhg improve BGP convergence
When IGP detects a BGP Nexthop is down, IGP would inform zebra on this route delete event. Zebra needs to make the following handlings. 
1. Find out all associated forwarding only nexthops resolved via this route. The nexthop lookup logic is similar to what it does in zebra_nhg_proto_add().
2. Trigger a back walk from each impacted nexthop to all associated PIC NHG and reresolve each PIC NHG
3. Update each PIC NHG in hardware. Sine PIC NHG is shared by VPN routes, it could quickly stop traffic loss before BGP reconvergence.
4. BGP nexthop down event would lead to BGP reconvergence which would update CONTEXT properly later. 

#### SRv6 VPN SAI Objects
The following diagram shows SAI objects related to SRv6. The detail information could be found at
https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-IPv6-Segment-Routing-VPN.md

<figure align=center>
    <img src="images/srv6_sai_objs.png" >
    <figcaption>Figure 6. SRv6 VPN SAI Objects<figcaption>
</figure> 

#### Map APP_DB to SAI objects
<figure align=center>
    <img src="images/app_db_to_sai.png" >
    <figcaption>Figure 7. APP DB to SAI OBJs mapping<figcaption>
</figure> 

### Orchagent Modifications
Handle two new forwarding objects from APP_DB, NEXTHOP_TABLE and PIC_CONTEXT_TABLE.  Orchagent would map proper objects to the proper SAI objects.

## Zebra handles NHG member down events
### Local link down events
In Local link down event which would not triger BGP NH's reachability change case, we expect BGP NHG should not be updated. 
TODO: Need to check with Kentaro to see if they would handle this event as the part of NHG handling.

### BGP NH down events
BGP NHG not reachable could be triggered from eBGP events or local link down events. We want zebra to backwalk all related BGP PIC NHG and update these NHG directly. 
1. After a routing update occurs, update the processing result of this route in rib_process_result and call zebra_rib_evaluate_rn_nexthops.

2. In the zebra_rib_evaluate_rn_nexthops function, construct a pic_nhg_hash_entry based on rn->p and find the corresponding pic_nhg. Based on the dependents list stored in pic_nhg, find all other nexthop groups associated with the current nhg, and then remove the nexthop members in these nexthop groups.

3. Trigger a refresh of pic_nhg to fpm.

4. To ensure that nhg refresh messages can be triggered first, add prectxqueue in fpm_nl_ctx as a higher-priority downstream queue for fnc. When triggering nhg updates, attach the nhg's ctx to prectxqueue, and when refreshing fpm, prioritize getting ctx from prectxqueue for downstream.

As shown in the following image：

<figure align=center>
    <img src="images/BGP_NH_update.png" >
    <figcaption>Figure 8. BGP NH down event Handling<figcaption>
</figure> 

When the route 2033::178, marked in blue, is deleted, find its corresponding nhg(68) based on 2033::178. Then, iterate through the Dependents list of nhg(68) and find the dependent nhg(67). Remove the nexthop member(2033::178) from nhg(67). After completing this action, trigger a refresh of nhg(67) to fpm.

Similarly, when the route 1000::178, marked in brown, is deleted, find its corresponding nhg(66). Based on the dependents list of nhg(66), find nhg(95) and remove the nexthop member(1000::178) from nhg(95). After completing this action, trigger a refresh of nhg(95) to fpm.

## Unit Test
### FRR Topotest
Add a new SRv6 VPN topotest test topology, and use fpm simulator to check fpm output with the following scenarios.
1. Normal set up
2. Simulate IGP NH down event via shutting down an IGP link
3. Simulate BGP NH down event via shutting down remote BGP session. 

### SONiC mgmt test
Add a new SRv6 VPN test in sonic_mgmt. 

**Note:** <span style="color:red">we may not be able to upstream this part as Cisco Silicon one's dataplane simulator has not been upstreamed to vSONiC yet. </span>

## References
- https://datatracker.ietf.org/doc/draft-ietf-rtgwg-bgp-pic/
- https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-IPv6-Segment-Routing-VPN.md
- https://github.com/sonic-net/SONiC/pull/1425


