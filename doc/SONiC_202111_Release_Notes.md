# SONiC 202111 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202111](https://github.com/sonic-net/SONiC/wiki/Release-Progress-Tracking-202111) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/sonic-net/sonic-buildimage/tree/202111 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_5.10.0-8-2-$(5.10.46-4)  |
| SAI   version             | SAI v1.9.1    |
| FRR                       | 7.5.1   |
| LLDPD                     | 1.0.4-1    |
| TeamD                     | 1.28-1    |
| SNMPD                     | 5.9+dfsg-3+b1    |
| Python                    | 3.6.0-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.17-2~bpo9+1    |
| isc-dhcp                  | 4.4.1-2   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Migrated to Bullseye (Debian version 11)	|

# Security Updates

1. Kernel upgraded from 4.19.152-1 to 5.10.46-4 for SONiC release.<br>
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-5.10.46-4

2. Docker upgraded from 18.09.8\~3-0\~debian-stretch to 20.10.7\~3-0\~debian-stretch.<br>
   Change log: https://docs.docker.com/engine/release-notes/#20107 


# Feature List

#### ACL orch redesign
This feature covers ACL rule counters support and enhancements in that area. The current design of ACL rule counters implements polling at orchagent side at a constant hardcoded interval of 10 seconds. While it is a simpler approach comparing to Flex Counters infrastructure it comes at a cost of scalability and performance issues.Flex counters infrastructure on another hand already used for port, PG, queue, watermark counters solves this issue by delegating counter polling to a separate thread in syncd and allowing to configure polling interval as well.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/acl/ACL-Flex-Counters.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** :  [533](https://github.com/sonic-net/sonic-swss-common/pull/533), [953](https://github.com/sonic-net/sonic-sairedis/pull/953), [1943](https://github.com/sonic-net/sonic-swss/pull/1943), [1858](https://github.com/sonic-net/sonic-utilities/pull/1858), [8908](https://github.com/sonic-net/sonic-buildimage/pull/8908) & [8909](https://github.com/sonic-net/sonic-buildimage/pull/8909)
 
#### App extension CLI generation tool 
The SONiC CLI Auto-generation tool - is a utility for generating the command-line interface for third-party features, called application extensions, that provide their functionality as separate docker containers. The YANG model will be used to describe the CONFIG DB schema and CLI will be generated according to CONFIG DB schema. The YANG model will serve as an input parameter for the SONiC Auto-generation utility. The CLI should be a part of SONiC utilities and support - show, config operations.
     
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-application-extention/sonic-application-extention-hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [780](https://github.com/sonic-net/SONiC/pull/780), [1644](https://github.com/sonic-net/sonic-utilities/pull/1644) & [1650](https://github.com/sonic-net/sonic-utilities/pull/1650)
          
#### Automatic techsupport and core dump creation 
Currently, techsupport is run by invoking show techsupport either by orchestration tools like Jenkins or manually. The techsupport dump also collects any core dump files available in the /var/core/ directory. However if the techsupport invocation can be made event-driven based on core dump generation, that would definitely improve the debuggability. 
 
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/61a07b416d0ecab85833337944928dca5d64150e/doc/auto_techsupport_and_coredump_mgmt.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [818](https://github.com/sonic-net/SONiC/pull/818), [8670](https://github.com/sonic-net/sonic-buildimage/pull/8670) & [1796](https://github.com/sonic-net/sonic-utilities/pull/1796)
               
#### Better route scalability with multiple next-hops 
Currently the route table within APP_DB contains all next hop information for a route embedded in that route's entry in the table. At high scale (particularly when handling millions of routes all routed over multiple next hops) this is inefficient both in terms of performance and occupancy. A more efficient system would involve managing the next hop groups in use by the route table separately, and simply have the route table specify a reference to which next hop group to use. Since at scale many routes will use the same next hop groups, this requires much smaller occupancy per route, and so more efficient building, transmission and parsing of per-route information.
    
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/ip/next_hop_group_hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [712](https://github.com/sonic-net/SONiC/pull/712), [475](https://github.com/sonic-net/sonic-swss-common/pull/475) & [1702](https://github.com/sonic-net/sonic-swss/pull/1702)
          
#### Class-Based Forwarding      
Class Based Forwarding which allows traffic to be steered through the network by policy, adding a layer of traffic engineering based on a Forwarding Class value which allows custom paths to be configured for a destination based on this value.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/e65d05a32761ea1c50c170008b22410879dce300/doc/cbf/cbf_hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [796](https://github.com/sonic-net/SONiC/pull/796), [525](https://github.com/sonic-net/sonic-swss-common/pull/525), [909](https://github.com/sonic-net/sonic-sairedis/pull/909), [1963](https://github.com/sonic-net/sonic-swss/pull/1963), [8689](https://github.com/sonic-net/sonic-buildimage/pull/8689) & [1799](https://github.com/sonic-net/sonic-utilities/pull/1799)
                    
#### CLI level authorization      
This feature is based on TACACS+ Authentication, and provides a detailed description for improved TACACS+ support.

SONiC currently supported TACACS+ features:

***Authentication:***

	* 	User session authorization.
	*	User session accounting.
	*	User command authorization with local permission.

***New features:***

	*	User command authorization with TACACS+ server.
	*	User command accounting with TACACS+ server.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/4d1660cc88002aff64e6228b63b5f2d6b59d6031/doc/aaa/TACACS%2B%20Design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [813](https://github.com/sonic-net/SONiC/pull/813), [8660](https://github.com/sonic-net/sonic-buildimage/pull/8660), [8659](https://github.com/sonic-net/sonic-buildimage/pull/8659), [8715](https://github.com/sonic-net/sonic-buildimage/pull/8715), [9029](https://github.com/sonic-net/sonic-buildimage/pull/9029), [1889](https://github.com/sonic-net/sonic-utilities/pull/1889), [4605](https://github.com/sonic-net/sonic-mgmt/pull/4605) & [8750](https://github.com/sonic-net/sonic-buildimage/pull/8750)
                     
#### DHCP support IPv6     
SONiC currently supports DHCPv4 Relay via the use of open source ISC DHCP package. However, DHCPv6 specification does not define a way to communicate client link-layer address to the DHCP server where DHCP server is not connected to the same network link as DHCP client. DHCPv6 requires all clients prepare and send a DUID as the client identifier in all DHCPv6 message exchanges. 
       
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/92acec6cc29165382e0b40d1ff528a6f409de572/doc/DHCPv6_relay/DHCPv6-relay-agent-High-Level-Design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [787](https://github.com/sonic-net/SONiC/pull/787)
              
#### Dynamic Policy Based Hashing       
This feature will support policy based hashing for NVGRE/VxLAN packets based on inner 5-tuple (IP proto, L4 dst/src port, IPv4/IPv6 dst/src)

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/91eee7f952b4ad4679ada1b5b5f3b95ad39e2431/doc/pbh/pbh-design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [773](https://github.com/sonic-net/SONiC/pull/773), [7461](https://github.com/sonic-net/sonic-buildimage/pull/7461), [495](https://github.com/sonic-net/sonic-swss-common/pull/495), [1782](https://github.com/sonic-net/sonic-swss/pull/1782) & [1701](https://github.com/sonic-net/sonic-utilities/pull/1701)
          
#### Dynamic port breakout         
This feature is to support port breakout dynamically. We should be able to change port breakout mode at run time without affecting the unrelated port activities. Configuration dependencies on the ports to be changed with breakout mode should be reported or removed automatically. Run time dependencies and resources should be cleared on the ports to be changed with breakout mode. Optionally, we provide a way to automatically add the configuration back to the port if operators can specify in advance.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4235](https://github.com/sonic-net/sonic-buildimage/pull/4235), [3910](https://github.com/sonic-net/sonic-buildimage/pull/3910), [1242](https://github.com/sonic-net/sonic-swss/pull/1242), [1219](https://github.com/sonic-net/sonic-swss/pull/1219), [1148](https://github.com/sonic-net/sonic-swss/pull/1148), [1112](https://github.com/sonic-net/sonic-swss/pull/1112), [766](https://github.com/sonic-net/sonic-utilities/pull/766), [72](https://github.com/sonic-net/sonic-platform-common/pull/72), [859](https://github.com/sonic-net/sonic-utilities/pull/859), [767](https://github.com/sonic-net/sonic-utilities/pull/767), [765](https://github.com/sonic-net/sonic-utilities/pull/765), [3912](https://github.com/sonic-net/sonic-buildimage/pull/3912), [3911](https://github.com/sonic-net/sonic-buildimage/pull/3911), [3909](https://github.com/sonic-net/sonic-buildimage/pull/3909), [3861](https://github.com/sonic-net/sonic-buildimage/pull/3861), [3730](https://github.com/sonic-net/sonic-buildimage/pull/3730), [3907](https://github.com/sonic-net/sonic-buildimage/pull/3907), [3891](https://github.com/sonic-net/sonic-buildimage/pull/3891), [3874](https://github.com/sonic-net/sonic-buildimage/pull/3874), [1085](https://github.com/sonic-net/sonic-swss/pull/1085), [1151](https://github.com/sonic-net/sonic-swss/pull/1151) & [1150](https://github.com/sonic-net/sonic-swss/pull/1150)
                
#### EXP to TC QoS maps          
This feature extends SONiC to support MPLS TC to TC mappings. This new enhancement adds support to SONiC for MPLS TC to TC map which allows QoS to work on MPLS packets. User can configure MPLS TC to TC map at start-of-day via configuration file. CLI support will exist to offer the same amount of support as for DSCP to TC map.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/bb476c589a6ac5a7e3ea66a0a84caab6264dc7a9/doc/qos/mpls_tc_to_tc_map.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [844](https://github.com/sonic-net/SONiC/pull/844), [537](https://github.com/sonic-net/sonic-swss-common/pull/537), [1954](https://github.com/sonic-net/sonic-swss/pull/1954) & [1875](https://github.com/sonic-net/sonic-utilities/pull/1875)
               
#### EVPN VXLAN  for platforms using P2MP tunnel based L2 forwarding  
The EVPN VXLAN feature implementation is based on RFC 7432 and 8365 in SONiC. This feature is incremental to the SONiC.201911 release.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/17583e3eae8e06cf9e15df9806ab97ab4db76082/doc/vxlan/EVPN/EVPN_VXLAN_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [806](https://github.com/sonic-net/SONiC/pull/806), [1858](https://github.com/sonic-net/sonic-swss/pull/1858), [8685](https://github.com/sonic-net/sonic-buildimage/pull/8685), [920](https://github.com/sonic-net/sonic-sairedis/pull/920), [1859](https://github.com/sonic-net/sonic-swss/pull/1859), [886](https://github.com/sonic-net/sonic-sairedis/pull/886), [519](https://github.com/sonic-net/sonic-swss-common/pull/519), [1748](https://github.com/sonic-net/sonic-utilities/pull/1748) & [8369](https://github.com/sonic-net/sonic-buildimage/pull/8369)
          
#### Handle port config change on fly in xcvrd       
The current xcvrd assumes that port mapping information is never changed, so it always read static port mapping information from platform.json/port_config.ini and save it to a global data structure. However, things changed since dynamic port breakout feature introduced. Port can be added/created on the fly, xcvrd cannot update transceiver information, DOM information and transceiver status information without knowing the ports change. This implementation introduces a way to handle port configuration change on fly in xcvrd.
   
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/xrcvd/transceiver-monitor-hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [839](https://github.com/sonic-net/SONiC/pull/839) & [212](https://github.com/sonic-net/sonic-platform-daemons/pull/212)
          
#### Host interface trap counter           
Flow counters are usually used for debugging, troubleshooting and performance enhancement processes. Flow counters could cover cases like, Host interface traps (number of received traps per Trap ID), Routes matching the configured prefix pattern (number of hits and number of bytes), FDB entries matching the configured VXLAN tunnel or using the VLAN ID as pattern, Next-Hop/Next-Hop Group/Next-Hop Group Member,  & This document focus on host interface traps counter.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/434a5fcc8a5c7f0fe13e163d89ee9af61a06dbd1/doc/flow_counters/flow_counters.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [858](https://github.com/sonic-net/SONiC/pull/858), [8940](https://github.com/sonic-net/sonic-buildimage/pull/8940), [1951](https://github.com/sonic-net/sonic-swss/pull/1951), [4456](https://github.com/sonic-net/sonic-mgmt/pull/4456), [1868](https://github.com/sonic-net/sonic-utilities/pull/1868), [954](https://github.com/sonic-net/sonic-sairedis/pull/954), [534](https://github.com/sonic-net/sonic-swss-common/pull/534), [1876](https://github.com/sonic-net/sonic-utilities/pull/1876) &  [9353](https://github.com/sonic-net/sonic-buildimage/pull/9353)
          
#### L2 functional and performance enhancements       
This implentation provides enhancements in SONiC layer 2 forwarding for FDB flush, MAC move, FDB aging time configuration, Static FDB configuration and VLAN Range configuration.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/layer2-forwarding-enhancements/SONiC%20Layer%202%20Forwarding%20Enhancements%20HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [379](https://github.com/sonic-net/SONiC/pull/379), [510](https://github.com/sonic-net/sonic-sairedis/pull/510), [303](https://github.com/sonic-net/sonic-swss-common/pull/303), [529](https://github.com/sonic-net/sonic-utilities/pull/529) & [1716](https://github.com/sonic-net/sonic-swss/pull/1716)
          
#### New branch creation for Debian11    
In preparation for Debian Bullseye, upgrade SONiC's base system to be based on Bullseye, which was released in August 2021.Kernel is now based on 5.10.x (currently, official Debian Bullseye is publishing the 5.10.70 kernel) Most Python 2 packages (as well as pip2.7) have been removed from Bullseye. The Python 2 interpreter is still available. The kernel has been upgraded to 5.10.46, and the base system is now based on Bullseye. Containers are still based on Buster.
     
Refer [PR#8191](https://github.com/sonic-net/sonic-buildimage/pull/8191) for more details. 
          
#### One line command to extract multiple DBs info of a SONiC component  
In SONiC, there usually exists a set of tables related/relevant to a particular module. All of these have to be looked at to confirm whether any configuration update is properly applied and propagated.The task of debugging quickly becomes tedious because currently, there is no utility which does print a unified view of the redis-state. This is the problem which is addressed by this dump utility.This utility provides the base infrastructure and guidelines to make is easy for the developers to extend and support the utility for different modules.
 
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/Dump-Utility.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [789](https://github.com/sonic-net/SONiC/pull/789), [1666](https://github.com/sonic-net/sonic-utilities/pull/1666), [1667](https://github.com/sonic-net/sonic-utilities/pull/1667), [1668](https://github.com/sonic-net/sonic-utilities/pull/1668), [1669](https://github.com/sonic-net/sonic-utilities/pull/1669), [1670](https://github.com/sonic-net/sonic-utilities/pull/1670), [1853](https://github.com/sonic-net/sonic-utilities/pull/1853), [1877](https://github.com/sonic-net/sonic-utilities/pull/1877), [1913](https://github.com/sonic-net/sonic-utilities/pull/1913) & [1892](https://github.com/sonic-net/sonic-utilities/pull/1892)
          
#### Overlay ECMP        
This feature provides Vxlan Overlay ECMP feature implementation in SONiC with BFD support. This is an extension to the existing VNET Vxlan support as defined in the Vxlan HLD. 
        
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/b9f1e94235553c825de67d244c9e8836f369b965/doc/vxlan/Overlay%20ECMP%20with%20BFD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [861](https://github.com/sonic-net/SONiC/pull/861), [1960](https://github.com/sonic-net/sonic-swss/pull/1960), [9197](https://github.com/sonic-net/sonic-uildimage/pull/9197), [96](https://github.com/sonic-net/sonic-restapi/pull/96), [1955](https://github.com/sonic-net/sonic-swss/pull/1955)[903](https://github.com/sonic-net/sonic-sairedis/pull/903), [1883](https://github.com/sonic-net/sonic-swss/pull/1883) & [1942](https://github.com/sonic-net/sonic-utilities/pull/1942)
          
#### PDK - Platform Development Environment 
SONiC OS is portable across different network devices with supported ASIC via Switch Abstraction Interface (SAI). These devices primarily differ in the way various device specific hardware components are accessed, and thus require custom device drivers and python plugins. Each platform vendor implements these custom device drivers and plugins. The feature requirement is to support a SONiC platform driver development framework to enable rapid development of custom device drivers and plugins.
      
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/platform/brcm_pdk_pddf.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [3387](https://github.com/sonic-net/sonic-buildimage/pull/3387), [624](https://github.com/sonic-net/sonic-utilities/pull/624), [62](https://github.com/sonic-net/sonic-platform-common/pull/62)
          
#### PINS (P4 Integrated Network Stack)    
This feature describes PINS (P4 Integrated Network Stack), a P4RT based SDN interface for SONiC. P4RT for SONiC is opt-in, has familiar interfaces, enables rapid innovation, provides automated validation, and serves as unambiguous documentation. A canonical family of P4 programs documents the packet forwarding pipeline of SAI. Remote SDN controllers will use these P4 programs to control the switch forwarding behavior over the P4RT API.
          
Refer [HLD document](https://github.com/pins/SONiC/blob/pins-hld/doc/pins/pins_hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [841](https://github.com/sonic-net/SONiC/issues/841), [809](https://github.com/sonic-net/SONiC/pull/809), [826](https://github.com/sonic-net/SONiC/pull/826), [825](https://github.com/sonic-net/SONiC/pull/825), [840](https://github.com/sonic-net/SONiC/pull/840), [852](https://github.com/sonic-net/SONiC/pull/852), [846](https://github.com/sonic-net/SONiC/pull/846), [850](https://github.com/sonic-net/SONiC/pull/850) & [836](https://github.com/sonic-net/SONiC/pull/836)
          
#### Reclaim reserved buffer for unused ports       
Originally, the reserved buffer is reclaimed by removing buffer objects of the unused ports. However, this introduces inconsistency. To resolve this zero buffer profiles are introduced to indicate 0 reserved size of a buffer object. Removing a buffer object indicates setting the buffer object to SDK default value.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/qos/reclaim-reserved-buffer-images/reclaim-reserved-buffer-sequence-flow.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [831](https://github.com/sonic-net/SONiC/pull/831)
          
#### Routed sub-interface naming convention    
A sub port interface is a logical interface that can be created on a physical port or a port channel. A sub port interface serves as an interface to either a .1D bridge or a VRF, but not both. This feature design focuses on the use case of creating a sub port interface on a physical port or a port channel and using it as a router interface to a VRF.
       
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/d1b715a9cc762eff084d953581633e2a94115bac/doc/subport/sonic-sub-port-intf-hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [833](https://github.com/sonic-net/SONiC/pull/833), [2017](https://github.com/sonic-net/sonic-swss/pull/2017), [1907](https://github.com/sonic-net/sonic-swss/pull/1907), [8761](https://github.com/sonic-net/sonic-buildimage/pull/8761) & [1821](https://github.com/sonic-net/sonic-utilities/pull/1821)
          
#### SONiC for MPLS Dataplane   
This implementation is about the initial support for MPLS in SONiC infrastructure. The focus of this initial MPLS support is to expand existing SONiC infrastructure for IPv4/IPv6 routing to include equivalent MPLS functionality. The expected use case for this initial MPLS support is static LSP routing.
          
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/dc4a7ae5be75e8e376f9e95692e678aee0fb5dac/doc/mpls/MPLS_hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [706](https://github.com/sonic-net/SONiC/pull/706), [1181](https://github.com/opencomputeproject/SAI/pull/1181), [815](https://github.com/sonic-net/sonic-sairedis/pull/815), [824](https://github.com/sonic-net/sonic-sairedis/pull/824), [469](https://github.com/sonic-net/sonic-swss-common/pull/469), [7195](https://github.com/sonic-net/sonic-buildimage/pull/7195), [1686](https://github.com/sonic-net/sonic-swss/pull/1686), [1537](https://github.com/sonic-net/sonic-utilities/pull/1537), [1871](https://github.com/sonic-net/sonic-swss/pull/1871), [7881](https://github.com/sonic-net/sonic-buildimage/pull/7881) & [3483](https://github.com/sonic-net/sonic-mgmt/pull/3483)

#### SONiC Generic Update and Rollback           
The SONiC Generic Update and Rollback feature is to standardize the way to do partial updates, to take checkpoints and finally to rollback the configurations for SONiC.

Refer [HLD document](https://github.com/ghooo/SONiC/blob/c1f3f3b5427d0cafb3defd93df8b906a26fcee8a/doc/config-generic-update-rollback/SONiC_Generic_Config_Update_and_Rollback_Design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [736](https://github.com/sonic-net/SONiC/pull/736), [1536](https://github.com/sonic-net/sonic-utilities/pull/1536), [1599](https://github.com/sonic-net/sonic-utilities/pull/1599),  [1762](https://github.com/sonic-net/sonic-utilities/pull/1762),  [1794](https://github.com/sonic-net/sonic-utilities/pull/1794),  [1831](https://github.com/sonic-net/sonic-utilities/pull/1831),  [1856](https://github.com/sonic-net/sonic-utilities/pull/1856),  [1864](https://github.com/sonic-net/sonic-utilities/pull/1864),  [1885](https://github.com/sonic-net/sonic-utilities/pull/1885),  [1901](https://github.com/sonic-net/sonic-utilities/pull/1901),  [1919](https://github.com/sonic-net/sonic-utilities/pull/1919),  [1923](https://github.com/sonic-net/sonic-utilities/pull/1923),  [1929](https://github.com/sonic-net/sonic-utilities/pull/1929),  [1934](https://github.com/sonic-net/sonic-utilities/pull/1934),  [1969](https://github.com/sonic-net/sonic-utilities/pull/1969),  [1973](https://github.com/sonic-net/sonic-utilities/pull/1973),  [1977](https://github.com/sonic-net/sonic-utilities/pull/1977),  [1981](https://github.com/sonic-net/sonic-utilities/pll/1981),  [1983](https://github.com/sonic-net/sonic-utilities/pull/1983),  [1987](https://github.com/sonic-net/sonic-utilities/pull/1987),  [1988](https://github.com/sonic-net/sonic-utilities/pull/1988),  [2003](https://github.com/sonic-net/sonic-utilities/pull/2003),  [2006](https://github.com/sonic-net/sonic-utilities/pull/2006),  [2008](https://github.com/sonic-net/sonic-utilities/pull/2008),  [2015](https://github.com/sonic-net/sonic-utilities/pull/2015),  [2020](https://github.com/sonic-net/sonic-utilities/pull/2020) & [2028](https://github.com/sonic-net/sonic-utilities/pull/2028) 
          
#### SRv6 support (Cntd)           
SRv6 has been widely adopted as an IPv6 based SDN solution, which provides programming ability, TE capabilities, and deployment simplicity to network administrators. With current support from a rich ecosystem, including major ASIC manufactures, networking vendors and open source communities, the deployment of SRv6 is accelerating. This implentation adds SRv6 into SONIC to benefit users in DC as well as beyond DC.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/faa432df6185f7c04d896285db61ac86300161c9/doc/srv6/srv6-hld-v19.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [795](https://github.com/sonic-net/SONiC/pull/795), [9238](https://github.com/sonic-net/sonic-buildimage/pull/9238), [538](https://github.com/sonic-net/sonic-swss-common/pull/538), [1964](https://github.com/sonic-net/sonic-swss/pull/1964) & [1883](https://github.com/sonic-net/sonic-utilities/pull/1883)
          
#### Upgrade  SONiC init flow          
This implentation is to introduce a new API for query statistics capabilities of counters in a faster and more efficient way. Currently on SONiC, in order to get the counters capabilities, SONiC is iterating all port stats one by one, to understand the supported capabilities. This operation is time consuming and the new API can reduce the time for this operation in one call.
     
Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/Query_Stats_Capability/Query_Stats_Capability_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [871](https://github.com/sonic-net/SONiC/pull/871) & [952](https://github.com/sonic-net/sonic-sairedis/pull/952)
          

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.9.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.9.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Alibaba, Aviz, Broadcom, DellEMC, Google, Intel, Juniper, LinkedIn, Marvell, Metaswitch, Microsoft & Nvidia.  

<br> 
