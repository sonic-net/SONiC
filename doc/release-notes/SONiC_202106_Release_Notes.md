# SONiC 202106 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202106](https://github.com/sonic-net/SONiC/wiki/Release-Progress-Tracking-202106) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/sonic-net/sonic-buildimage/tree/202106 <br>
Image  : https://sonic-jenkins.westus2.cloudapp.azure.com/  (Example - Image for Broadcom based platforms is [here]( https://sonic-jenkins.westus2.cloudapp.azure.com/job/broadcom/job/buildimage-brcm-202106/lastSuccessfulBuild/artifact/target/))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_4.19.0-12-2 (4.19.152-1)   |
| SAI   version             | SAI v1.8.1    |
| FRR                       | 7.5.1   |
| LLDPD                     | 1.0.4-1    |
| TeamD                     | 1.28-1    |
| SNMPD                     | 5.7.3+dfsg-1.5    |
| Python                    | 3.6.0-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.17-2~bpo9+1    |
| isc-dhcp                  |  4.4.1-2   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Continues to use Buster (Debian version 10)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 4.9.168-1+deb9u5 (SONiC Release 202006) to 4.19.152-1 for SONiC release.
   Change log: https://salsa.debian.org/kernel-team/linux/-/raw/buster-security/debian/changelog 

2. Plexus-utils fix: CVE-2017-1000487   


# Feature List

#### 1. Telemetry for Multi-ASIC
This feature is an enhancement on sonic_db_config package for multi-asic to read different namespace redis configuration. And enhanced V2R Lookup for multi-asic, enhanced gNMI Server to initiate redis connection, enhanced gNMI Server Get and enhanced the parsing of target in gNMI Request.<br>
<br> Refer [HLD document](https://github.com/sonic-net/sonic-telemetry/pull/77) and below mentioned PR's for more details. 
<br>**Pull Requests** : [77](https://github.com/sonic-net/sonic-telemetry/pull/77)


#### 2. Add FRR running configuration to tech support
This implementation is an enhancement on tech support as mentioned below.

*	Adding a --silent option to show techsupport command. 
*	Adding global and per-command timeouts. 
*	Adding time profiling information for the commands in techsupport. Time profiling information would be part of the tarball and helps to analyse the time consumption per command
*	Sometimes syncd docker is down and bcmshell is unavailable. In such cases all the bcmcmd commands would timeout and result in tremendous increase in the total techsupport collection time. We provided an option to skip rest of the bcmcmd commands once one command times out.
*	Added show services, show reboot-cause and various BGP, BFD, bcm shell and other commands

Refer [HLD document](https://github.com/sonic-net/sonic-utilities/pull/1249) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [5067](https://github.com/sonic-net/sonic-buildimage/issues/5067) , [1193](https://github.com/sonic-net/sonic-utilities/pull/1193)


#### 3. App extension with warmboot awareness
SONiC Application Extension Infrastructure is a SONiC infrastructure and framework for managing SONiC Application Packages which in this scope are SONiC compatible Docker images distributed individually from one another and from the base SONiC image.
<br>Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-application-extention/sonic-application-extention-hld.md) and below mentioned PR's for more details. 
<br>**Pull Requests** : [682](https://github.com/sonic-net/SONiC/pull/682), [6398](https://github.com/sonic-net/sonic-buildimage/issues/6398)

#### 4. Enable/Disable auto negotiation and speed setting with number of lanes
This feature introduces a few new CLI commands which will fit in sonic-utilities. And this feature also requires to change the configuration flow for port auto negotiation attributes which will be covered in orchagent.<br>
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/9b58ef06ab49b489e3aed287659100ce7be8c76a/doc/port_auto_neg/port-auto-negotiation-design.md#cli-enhancements) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [732](https://github.com/sonic-net/SONiC/pull/732), [6948](https://github.com/sonic-net/sonic-buildimage/pull/6948), [1568](https://github.com/sonic-net/sonic-utilities/pull/1568), [1714](https://github.com/sonic-net/sonic-swss/pull/1714), [3376](https://github.com/sonic-net/sonic-mgmt/pull/3376)


#### 5. TPID config support
Currently SONiC Testbed setup uses fanout switches to connect to the testbed server and running the PTF test cases. The fanout switch ports connecting to the DUT are configured as access ports. The fanout switch is configured with 802.1Q tunnel on the DUT facing ports side so that tagged packets are not to be used for service delimiting purpose. With this TPID configuration capability, these fanout switches can be converted to run in SONiC.<br>
<br> Refer [HLD document](https://github.com/gechiang/SONiC/blob/3f57d0304bda22222b01f2b90098e4d4d3b88f68/doc/tpid/SonicTPIDSettingHLD1.md) and below mentioned PR's for more details. 
<br>**Pull Requests** : [681](https://github.com/sonic-net/SONiC/pull/681), [7630](https://github.com/sonic-net/sonic-buildimage/pull/7630), [1747](https://github.com/sonic-net/sonic-swss/pull/1747), [1618](https://github.com/sonic-net/sonic-utilities/pull/1618)


#### 6. Error handling (swss)
This feature impliments the orchagent in handling SAI failures. below are the failure handling functions in orchagent

*	Allow different handling for Create/Set/Remove/Get operations.
*	Allow each Orch to have its specific handling logic.
*	Adapt handling logic based on SAI API type and SAI status.
*	Escalate the failure to upper layers when the failure cannot be handled in orchagent.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/SAI_failure_handling/SAI_failure_handling.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [1596](https://github.com/sonic-net/sonic-swss/pull/1596), [1815](https://github.com/sonic-net/sonic-swss/pull/1815), [1768](https://github.com/sonic-net/sonic-swss/pull/1768), [1786](https://github.com/sonic-net/sonic-swss/pull/1786), [1665](https://github.com/sonic-net/sonic-swss/pull/1665)


#### 7.Inband mgmt VRF
This feature design is intended to have a generic approach for in-band management via mgmt VRF feature. A user can set an attribute "in_band_mgmt_enabled" to the config_db for MGMT_VRF_CONFIG table entry. The default value if not specified would be "false"<br>
<br> Refer [HLD document](https://github.com/venkatmahalingam/SONiC/blob/7781c097a92d9fbac3fc2fe2f8c6ce175839f473/doc/vrf/SONiC_in_band_mgmt_via_mgmt_Vrf_HLD.md) and below mentioned PR's for more details. 
<br>**Pull Requests** : [1726](https://github.com/sonic-net/sonic-swss/pull/1726) 


#### 8.SONiC for MPLS Dataplane
This feature provides general information about the initial support for MPLS in SONiC infrastructure. The focus of this initial MPLS support is to expand existing SONiC infrastructure for IPv4/IPv6 routing to include equivalent MPLS functionality. The expected use case for this initial MPLS support is static LSP routing.<br>
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/364fcae0438ed583270b56319dcfcb91e20b918a/doc/mpls/MPLS_hld.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [1537](https://github.com/sonic-net/sonic-utilities/pull/1537), [469](https://github.com/sonic-net/sonic-swss-common/pull/469), [824](https://github.com/sonic-net/sonic-sairedis/pull/824), [7195](https://github.com/sonic-net/sonic-buildimage/pull/7195), [1686](https://github.com/sonic-net/sonic-swss/pull/1686)


#### 9.IPv6 Link Local and BGP Unnumbered
This feature provides the implementation of IPv6 link-local enhancements in SONiC.
<br> Refer [HLD document](https://github.com/kirankella/SONiC/blob/d17a977f88ed623c8367eaac747040796d7a7c3f/doc/ipv6/ipv6_link_local.md) and below mentioned PR's for more details.
<br>**Pull Requests** : [5584](https://github.com/sonic-net/sonic-buildimage/pull/5584), [1463](https://github.com/sonic-net/sonic-swss/pull/1463), [1159](https://github.com/sonic-net/sonic-utilities/pull/1159)


#### 10. MC-LAG (L2)
This feature is an enhancements of SONiC ICCP MCLAG. This includes MCLAG configuration support, data structure changes, MAC event handling optimizations for scaling performance, support of static MAC address over MCLAG, support bridge-port isolation group for BUM control to MCLAG, and traffic recovery sequencing for traffic loop prevention.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/mclag/MCLAG_Enhancements_HLD.md) and below mentioned PR's for more details.
<br> **Pull Requests** :  [596](https://github.com/sonic-net/SONiC/pull/596), [885](https://github.com/sonic-net/sonic-swss/pull/885), [4819](https://github.com/sonic-net/sonic-buildimage/pull/4819), [1331](https://github.com/sonic-net/sonic-swss/pull/1331), [1349](https://github.com/sonic-net/sonic-swss/pull/1349), [529](https://github.com/sonic-net/sonic-utilities/pull/529), [405](https://github.com/sonic-net/sonic-swss-common/pull/405), [59](https://github.com/sonic-net/sonic-mgmt-framework/pull/59), [25](https://github.com/sonic-net/sonic-mgmt-common/pull/25)

#### 11. DHCP relay IPv6 support
This DHCP Relay for IPv6 feature in SONiC impliments the following functionalities, 

*	To give the support for relaying DHCP packets from downstream networks to upstream networks using IPv6 addresses.
*	To provide the functionality as a seperate process running on dhcp-relay docker container.
*	To relay messages to multiple unicast and multicast addresses.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/DHCPv6_Relay/DHCPv6_Relay_HLD.md) and below mentioned PR's for more details.
<br> **Pull Requests** : [7772](https://github.com/sonic-net/sonic-buildimage/pull/7772), [6531](https://github.com/sonic-net/sonic-buildimage/pull/6531), [7789](https://github.com/sonic-net/sonic-buildimage/pull/7789), [3565](https://github.com/sonic-net/sonic-mgmt/pull/3565)

#### 12. RADIUS AAA
This implementation describes the high level design of RADIUS management user authentication feature in SONiC.<br>
<br> Refer [HLD document](https://github.com/a-barboza/SONiC/blob/8d31c4014e27f422f4c522d2891fa9d9a4fff606/doc/aaa/radius_authentication.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [500](https://github.com/sonic-net/SONiC/pull/500), [1521](https://github.com/sonic-net/sonic-utilities/pull/1521), [7284](https://github.com/sonic-net/sonic-buildimage/pull/7284), [4220](https://github.com/sonic-net/sonic-buildimage/pull/4220)


#### 13. PDK - Platform Development Environment
The SONiC PDE is part of the SONiC Platform Development Kit (PDK) which optimizes platform development. The SONiC PDK consists of PDDF (Platform Driver Development Framework) and PDE (Platform Development Environment)
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/platform/pde.md) and below mentioned PR's for more details.
<br> **Pull Requests** : [3778](https://github.com/sonic-net/sonic-buildimage/pull/3778) [28](https://github.com/sonic-net/sonic-platform-pdk-pde/pull/28), [107](https://github.com/Azure/sonic-build-tools/pull/107).


#### 14. Broadcom silicon common config
This feature supports the per-switching silicon common config.bcm file to assist with silicon-wide application configuration settings for all affected Broadcom platforms. The infrastructure saves development time by allowing applications to refactor common settings in a single location, and allows for platform-specific overrides.<br>
<br> Refer [HLD document](https://github.com/geans-pin/SONiC/blob/ff5ad50dfd770242d4fdac97f2e4c803b2425dde/doc/platform/common_config.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [693](https://github.com/sonic-net/sonic-sairedis/pull/693), [699](https://github.com/sonic-net/SONiC/pull/699), [5818](https://github.com/sonic-net/sonic-buildimage/pull/5818), [7493](https://github.com/sonic-net/sonic-buildimage/pull/7493)


#### 15. PCIe Monitoring
This feature is intended to give the idea of how to monitor the platform PCIe devices and alert of any problems on PCIe buses and devices on SONiC using pcie-check service and pcied on PMON container.New PCIe Monitor service is designed to use the PcieUtil utility to check the current status of PCIe devices and buses and alert if there is any missing devices or any error while communicating on the PCIe buses.PCIe device monitoring will be done in two separate services, pcie-check.service which is a systemd service, will check the PCIe device during the boot time and pcied which is a daemon in PMON container will monitor during the runtime.<br>
<br> Refer [HLD document](https://github.com/sujinmkang/SONiC/blob/4e93b8b30609ffc698ac801cd12740c35d2ea284/doc/pcie-mon/pcie-monitoring-services-hld.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [60](https://github.com/sonic-net/sonic-platform-daemons/pull/60), [100](https://github.com/sonic-net/sonic-platform-daemons/pull/100), [144](https://github.com/sonic-net/sonic-platform-common/pull/144), [634](https://github.com/sonic-net/SONiC/pull/634), [678](https://github.com/sonic-net/SONiC/pull/678), [1169](https://github.com/sonic-net/sonic-utilities/pull/1169), [5000](https://github.com/sonic-net/sonic-buildimage/pull/5000)


#### 16. Enhanced xcrvd SFP error flow HLD
This feature reflects the current implementation of xcvrd to the HLD.Added new SFP error event handling procedure and added a CLI to retrieve the SFP error status.<br>
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/f8893cf5d7492c92e9e613c1eb525778ab60f6cb/doc/xrcvd/transceiver-monitor-hld.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [184](https://github.com/sonic-net/sonic-platform-daemons/pull/184), [194](https://github.com/sonic-net/sonic-platform-common/pull/194), [586](https://github.com/sonic-net/SONiC/pull/586), [1658](https://github.com/sonic-net/sonic-utilities/pull/1658), [3648](https://github.com/sonic-net/sonic-mgmt/pull/3648), [7605](https://github.com/sonic-net/sonic-buildimage/pull/7605)


#### 17. Entity sensor MIB extension
The Entity MIB contains several groups of MIB objects: entityPhysical group, entityLogical group and so on. Currently SONiC only implemented part of the entityPhysical group following RFC2737. Since entityPhysical group is mostly common used, this extension will focus on entityPhysical group and leave other groups for future implementation. <br>
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/90731187a760b604870a2f3fc6868530f5427937/doc/snmp/extension-to-physical-entity-mib.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [211](https://github.com/sonic-net/sonic-snmpagent/pull/211), [766](https://github.com/sonic-net/SONiC/pull/766), [3357](https://github.com/sonic-net/sonic-mgmt/pull/3357)


#### 18. Enable/Disable auto negotiation and speed setting with number of lanes
Add new CLIs to enable/disable auto negotiation per interface as well as setting the number of lanes per requested speed <br>
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/9b58ef06ab49b489e3aed287659100ce7be8c76a/doc/port_auto_neg/port-auto-negotiation-design.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [732] (https://github.com/sonic-net/SONiC/pull/732)

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.8.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.8.1%20Release%20notes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Broadcom, DellEMC, Innovium, Intel, Juniper, Metaswitch, Microsoft, Nvidia.   . 

<br>
