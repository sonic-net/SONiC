# SONiC 202012 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC 202012 release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202012 <br>
Image  : https://sonic-jenkins.westus2.cloudapp.azure.com/  (Example - Image for Broadcom based platforms is [here]( https://sonic-jenkins.westus2.cloudapp.azure.com/job/broadcom/job/buildimage-brcm-202012/lastSuccessfulBuild/artifact/target/))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_4.19.0-9-2 (4.19.118-2+deb10u1)   |
| SAI   version             | SAI v1.7.1    |
| FRR                       | 7.5    |
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


# Security Updates

1. Kernel upgraded from 4.9.110-3deb9u6 (SONiC Release 201904) to 4.9.168-1+deb9u5 in this SONiC release. 
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-4.9.168-1deb9u5
2. Docker upgraded from 18.09.2\~3-0\~debian-stretch to 18.09.8\~3-0\~debian-stretch. 
   Change log: https://docs.docker.com/engine/release-notes/#18098 

# Feature List

#### Consistent ECMP support (fine grain ECMP)
**Pull Requests** :  [1315](https://github.com/Azure/sonic-swss/pull/1315), [623](https://github.com/Azure/SONiC/pull/623), [1788](https://github.com/Azure/sonic-mgmt/pull/1788), [4985](https://github.com/Azure/sonic-buildimage/pull/4985), [374](https://github.com/Azure/sonic-swss-common/pull/374), [659](https://github.com/Azure/SONiC/pull/659), [1056](https://github.com/Azure/sonic-utilities/pull/1056), [5518](https://github.com/Azure/sonic-buildimage/pull/5518), [5198](https://github.com/Azure/sonic-buildimage/pull/5198), [693](https://github.com/Azure/SONiC/pull/693). 

#### Container warm restart (BGP/TeamD/SWSS/SyncD)
The goal of SONiC warm reboot is to be able restart and upgrade SONiC software without impacting the data plane. Warm restart of each individual process/docker is also part of the goal. Except for syncd and database docker, it is desired for all other network applications and dockers to support un-planned warm restart.
<br> **Pull Requests** :  [392](https://github.com/Azure/sonic-buildimage/pull/3992), [1036](https://github.com/Azure/sonic-utilities/pull/1036/files), [5223](https://github.com/Azure/sonic-buildimage/pull/5233),[5163](https://github.com/Azure/sonic-buildimage/pull/5163/files), [5108](https://github.com/Azure/sonic-buildimage/pull/5108/files) & [1036](https://github.com/Azure/sonic-utilities/pull/1036/files).

#### CoPP Config/Management
During SWSS start, the prebuilt copp.json file is loaded as part of start script swssconfig.sh and written to APP DB. CoppOrch then translates it to Host trap/policer tables and programmed to SAI. With this enhancement, the CoPP tables shall be loaded to Config DB instead of APP DB. The default CoPP json file shall be prebuilt to the image and loaded during initialization. Any Config DB entries present shall be configured overwriting the default CoPP tables. This also ensures backward compatibility. 
<br> **Pull Requests** : [358](https://github.com/Azure/sonic-swss-common/pull/358), [1333](https://github.com/Azure/sonic-swss/pull/1333), [4861](https://github.com/Azure/sonic-buildimage/pull/4861) & [1004](https://github.com/Azure/sonic-utilities/pull/1004)

#### Console Support for SONiC (Hardware)
 **Pull Requests** :[5571](https://github.com/Azure/sonic-buildimage/pull/5571) & [1155](https://github.com/Azure/sonic-utilities/pull/1155) 

#### Console Support for SONiC (SSH forwarding)
This feature describes the persist console configurations to control how to view/connect to a device via serial link.
<br> **Pull Requests** : [664](https://github.com/Azure/SONiC/pull/664), [673](https://github.com/Azure/SONiC/pull/673) ,[1117](https://github.com/Azure/sonic-utilities/pull/1117) , [1120](https://github.com/Azure/sonic-utilities/pull/1120), [1130](https://github.com/Azure/sonic-utilities/pull/1130) ,[1136](https://github.com/Azure/sonic-utilities/pull/1136) , [1166](https://github.com/Azure/sonic-utilities/pull/1166) , [1173](https://github.com/Azure/sonic-utilities/pull/1173), [1176](https://github.com/Azure/sonic-utilities/pull/1176) , [5438](https://github.com/Azure/sonic-buildimage/pull/5438) & [5717](https://github.com/Azure/sonic-buildimage/pull/5717).

#### Dynamic headroom calculation
This feature defines the solution on how the headroom is calculated by the well known formula based with the cable length and speed as input. Arbitrary cable length will be supported or dynamically calculation for short.
<br> **Pull Requests** : [1338](https://github.com/Azure/sonic-swss/pull/1338), [973](https://github.com/Azure/sonic-utilities/pull/973), [4881](https://github.com/Azure/sonic-buildimage/pull/4881), [1971](https://github.com/Azure/sonic-mgmt/pull/1971), [361](https://github.com/Azure/sonic-swss-common/pull/361)

#### Enable synchornous SAI APIs (error handling)
This feature enables the synchronous mode for a closed-loop execution if SAI APIs from orchagent. In contrast to the previous asynchronous mode which cannot properly handle SAI API failures, the synchronous mode can gracefully handle SAI API failures by conducting the proper actions in orchagent. Therefore, the synchronous mode can substantially improve the reliability of SONiC.
<br> **Pull Requests** : [5237](https://github.com/Azure/sonic-buildimage/pull/5237) , [650](https://github.com/Azure/sonic-buildimage/pull/650) , [652](https://github.com/Azure/sonic-buildimage/pull/652) , [653](https://github.com/Azure/sonic-buildimage/pull/653), [1094](https://github.com/Azure/sonic-utilities/pull/1094) & [5308](https://github.com/Azure/sonic-buildimage/pull/5308).

#### EVPN/VXLAN
This feature provides general information about the EVPN VXLAN feature implementation based on RFC 7432 and 8365 in SONiC. This feature covers the aspects of the SONiC software components for L2 & L3 EVPN support, including Orchestration agent submodules (FdbOrch, VXLANOrch, VrfOrch, RouteOrch, etc.), SAI objects, SwSS managers (VXLAN, VRF managers), interactions with Linux kernel, FRR (BGP, Zebra), and syncd modules (fpmsyncd, fdbsyncd, neighsyncd).
<br> **Pull Requests** : [339](https://github.com/Azure/sonic-swss-common/pull/339) ,[350](https://github.com/Azure/sonic-swss-common/pull/350) , [1264](https://github.com/Azure/sonic-swss/pull/1264) , [1266](https://github.com/Azure/sonic-swss/pull/1266) , [1318](https://github.com/Azure/sonic-swss/pull/1318) , [1267](https://github.com/Azure/sonic-swss/pull/1267) & [870](https://github.com/Azure/sonic-utilities/pull/870).

#### SONiC entity MIB extensions
The Entity MIB contains several groups of MIB objects: entityPhysical group, entityLogical group and so on. Currently SONiC only implemented part of the entityPhysical group following RFC2737. Since entityPhysical group is mostly common used, this extension will focus on entityPhysical group and leave other groups for future implementation. The group entityPhysical contains a single table called "entPhysicalTable" to identify the physical components of the system. 
<br> **Pull Requests** :  [134](https://github.com/Azure/sonic-platform-common/pull/134), [102](https://github.com/Azure/sonic-platform-daemons/pull/102), [5645](https://github.com/Azure/sonic-buildimage/pull/5645), [168](https://github.com/Azure/sonic-snmpagent/pull/168)  & [2379](https://github.com/Azure/sonic-mgmt/pull/2379)

#### FRR BGP NBI
This feature extends and provides unified configuration and management capability for FRR-BGP features used in SONiC. This allows the user to configure & manage FRR-BGP using SONiC Management Framework with Open Config data models via REST, gNMI and also provides access via SONiC Management Framework CLI as well.
<br> **Pull Requests** : [5142](https://github.com/Azure/sonic-buildimage/pull/5142)

#### Gearbox
The purpose of this feature is to describe PHY functionality and common interface to manage PHY. PHY support the physical layer functionality.  Which is connector between MAC(SerDes) to physical medium such as optical fiber or copper transceivers.  Necessity of PHY depends on platform/hardware design.  Some platforms may be supported without an PHY(PHY Less) or PHY supports as part of ASIC (Internal PHY) and some cases it might be External PHY. External PHY will be used to serve different purposes like gearbox, retimer, MACSEC  and multi gigabit ethernet phy transceivers etc. 
The PHY has interfaces to connect/communicate with peripherals such as MII interface, SPI interface, power supply, clock and reset, system side interface, and line side interface.
<br> **Pull Requests** : [347](https://github.com/Azure/sonic-swss-common/pull/347), [931](https://github.com/Azure/sonic-utilities/pull/931), [1321](https://github.com/Azure/sonic-swss/pull/1321), [624](https://github.com/Azure/sonic-sairedis/pull/624) & [4851](https://github.com/Azure/sonic-buildimage/pull/4851).

#### Kubernetes (docker to be controlled by Kubernetes)
This feature deals in depth with kubernetes-support. With this feature, an image could be downloaded from external repositaries and kubernetes does the deployment. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode is referred as "kubernetes mode". 
<br> **Pull Requests** : [5421](https://github.com/Azure/sonic-buildimage/pull/5421), [1133](https://github.com/Azure/sonic-utilities/pull/1133) 

#### Management Framework (Phase 2)
Management framework makes use of the translation library (Translib) written in golang to convert the data models exposed to the management clients into the Redis ABNF schema format. Supported management servers can make use of the Translib to convert the incoming payload to SONiC ABNF schema and vice versa depending on the incoming request. Translib will cater to the needs of REST and gNMI servers. Later the Translib can be enhanced to support other management servers if needed. This framework will support both standard and custom YANG models for communication with the corresponding management servers. 
<br> **Pull Requests** : [4799](https://github.com/Azure/sonic-buildimage/pull/4799),[4765](https://github.com/Azure/sonic-buildimage/pull/4765),[4840](https://github.com/Azure/sonic-buildimage/pull/4840),[35](https://github.com/Azure/sonic-telemetry/pull/35), [38](https://github.com/Azure/sonic-telemetry/pull/38),[126](https://github.com/Azure/sonic-build-tools/pull/126), [170](https://github.com/Azure/sonic-build-tools/pull/170), [10](https://github.com/Azure/sonic-mgmt-common/pull/10),[11](https://github.com/Azure/sonic-mgmt-common/pull/11), [12](https://github.com/Azure/sonic-mgmt-common/pull/12), [13](https://github.com/Azure/sonic-mgmt-common/pull/13), [15](https://github.com/Azure/sonic-mgmt-common/pull/15), [16](https://github.com/Azure/sonic-mgmt-common/pull/16), [18](https://github.com/Azure/sonic-mgmt-common/pull/18), [19](https://github.com/Azure/sonic-mgmt-common/pull/19), [20](https://github.com/Azure/sonic-mgmt-common/pull/20), [21](https://github.com/Azure/sonic-mgmt-common/pull/21), [22](https://github.com/Azure/sonic-mgmt-common/pull/22), [23](https://github.com/Azure/sonic-mgmt-common/pull/23), [26](https://github.com/Azure/sonic-mgmt-common/pull/26), [27](https://github.com/Azure/sonic-mgmt-common/pull/27), [28](https://github.com/Azure/sonic-mgmt-common/pull/28), [31](https://github.com/Azure/sonic-mgmt-common/pull/31), [32](https://github.com/Azure/sonic-mgmt-common/pull/32), [34](https://github.com/Azure/sonic-mgmt-common/pull/34), [35](https://github.com/Azure/sonic-mgmt-common/pull/35), [50](https://github.com/Azure/sonic-mgmt-framework/pull/50), [51](https://github.com/Azure/sonic-mgmt-framework/pull/51),[52](https://github.com/Azure/sonic-mgmt-framework/pull/52), [53](https://github.com/Azure/sonic-mgmt-framework/pull/65), [57](https://github.com/Azure/sonic-mgmt-framework/pull/57), [60](https://github.com/Azure/sonic-mgmt-framework/pull/60),[65](https://github.com/Azure/sonic-mgmt-framework/pull/65), [66](https://github.com/Azure/sonic-mgmt-framework/pull/66),  [67](https://github.com/Azure/sonic-mgmt-framework/pull/67), [68](https://github.com/Azure/sonic-mgmt-framework/pull/68), [69](https://github.com/Azure/sonic-mgmt-framework/pull/69),[71](https://github.com/Azure/sonic-mgmt-framework/pull/71), [5810](https://github.com/Azure/sonic-buildimage/pull/5810),[5920](https://github.com/Azure/sonic-buildimage/pull/5920),[72](https://github.com/Azure/sonic-mgmt-framework/pull/72), [73](https://github.com/Azure/sonic-mgmt-framework/pull/73), [5714](https://github.com/Azure/sonic-buildimage/pull/5714) [5553](https://github.com/Azure/sonic-buildimage/pull/5553), [390](https://github.com/Azure/sonic-swss-common/pull/390), [6148](https://github.com/Azure/sonic-buildimage/pull/6148),[61](https://github.com/Azure/sonic-telemetry/pull/61)

#### Merge common lib for C++ and python (SWSS common lib)
**Pull Requests** : [378](https://github.com/Azure/sonic-swss-common/pull/378) 

#### Move from Python2->python3
**Pull Requests** : [5886](https://github.com/Azure/sonic-buildimage/pull/5886), [6038](https://github.com/Azure/sonic-buildimage/pull/6038), [6162](https://github.com/Azure/sonic-buildimage/pull/6162), [6176](https://github.com/Azure/sonic-buildimage/pull/6176), [1542](https://github.com/Azure/sonic-swss/pull/1542)

#### Multi-ASIC 202006
This feature is for a platform with more than one ASIC present on it, which is defined as a multi ASIC platform. SONiC so far supports platforms with single ASIC, we are enhancing SONiC to support multiple ASIC platforms.
<br> **Pull Requests** : [4825](https://github.com/Azure/sonic-buildimage/pull/4825), [4895](https://github.com/Azure/sonic-buildimage/pull/4895), [4926](https://github.com/Azure/sonic-buildimage/pull/4926), [4932](https://github.com/Azure/sonic-buildimage/pull/4932), [4959](https://github.com/Azure/sonic-buildimage/pull/4959), [4973](https://github.com/Azure/sonic-buildimage/pull/4973), [5022](https://github.com/Azure/sonic-buildimage/pull/5022), [5113](https://github.com/Azure/sonic-buildimage/pull/5113), [5121](https://github.com/Azure/sonic-buildimage/pull/5121), [5122](https://github.com/Azure/sonic-buildimage/pull/5122), [5202](https://github.com/Azure/sonic-buildimage/pull/5202), [5221](https://github.com/Azure/sonic-buildimage/pull/5221), [5224](https://github.com/Azure/sonic-buildimage/pull/5224), [5235](https://github.com/Azure/sonic-buildimage/pull/5235), [5316](https://github.com/Azure/sonic-buildimage/pull/5316), [5329](https://github.com/Azure/sonic-buildimage/pull/5329), [5357](https://github.com/Azure/sonic-buildimage/pull/5357), [5358](https://github.com/Azure/sonic-buildimage/pull/5358), [5364](https://github.com/Azure/sonic-buildimage/pull/5364), [5418](https://github.com/Azure/sonic-buildimage/pull/5418), [5420](https://github.com/Azure/sonic-buildimage/pull/5420), [5436](https://github.com/Azure/sonic-buildimage/pull/5436), [5437](https://github.com/Azure/sonic-buildimage/pull/5437), [5446](https://github.com/Azure/sonic-buildimage/pull/5446), [5460](https://github.com/Azure/sonic-buildimage/pull/5460), [5479](https://github.com/Azure/sonic-buildimage/pull/5479), [5503](https://github.com/Azure/sonic-buildimage/pull/5503), [5548](https://github.com/Azure/sonic-buildimage/pull/5548), [87](https://github.com/Azure/sonic-platform-daemons/pull/87), [81](https://github.com/Azure/sonic-py-swsssdk/pull/81), [138](https://github.com/Azure/sonic-snmpagent/pull/138), [140](https://github.com/Azure/sonic-snmpagent/pull/140), [141](https://github.com/Azure/sonic-snmpagent/pull/141), [145](https://github.com/Azure/sonic-snmpagent/pull/145), [154](https://github.com/Azure/sonic-snmpagent/pull/154), [155](https://github.com/Azure/sonic-snmpagent/pull/155), [158](https://github.com/Azure/sonic-snmpagent/pull/158), [161](https://github.com/Azure/sonic-snmpagent/pull/161), [166](https://github.com/Azure/sonic-snmpagent/pull/166), [376](https://github.com/Azure/sonic-swss-common/pull/376), [856](https://github.com/Azure/sonic-utilities/pull/856), [917](https://github.com/Azure/sonic-utilities/pull/917), [978](https://github.com/Azure/sonic-utilities/pull/978), [999](https://github.com/Azure/sonic-utilities/pull/999), [1005](https://github.com/Azure/sonic-utilities/pull/1005), [1006](https://github.com/Azure/sonic-utilities/pull/1006), [1013](https://github.com/Azure/sonic-utilities/pull/1013), [1057](https://github.com/Azure/sonic-utilities/pull/1057), [1064](https://github.com/Azure/sonic-utilities/pull/1064), [1079](https://github.com/Azure/sonic-utilities/pull/1079), [1080](https://github.com/Azure/sonic-utilities/pull/1080), [1081](https://github.com/Azure/sonic-utilities/pull/1081), [1123](https://github.com/Azure/sonic-utilities/pull/1123), [1137](https://github.com/Azure/sonic-utilities/pull/1137) & [1127](https://github.com/Azure/sonic-utilities/pull/1127)

#### Multi-DB enhancement-Part 2
**Pull Requests** : [5773](https://github.com/Azure/sonic-buildimage/pull/5773) & [1205](https://github.com/Azure/sonic-utilities/pull/1205)

#### ONIE FW tools
SONiC FW utility uses platform API to interact with the various platform components. SONiC FW utility extends to support for the automatic firmware update based on "platform_components.json" under platform directory and next reboot option which is passed as a option for fwutil update all fw command. SONiC FW utility also extends to support for the automatic firmware update with a custom firmware package that can include any firmware update tool and the firmware update tool will be used for the firmware update if it's specified in the "platform_components.json".
**Pull Requests** : [1165](https://github.com/Azure/sonic-utilities/pull/1165), [106](https://github.com/Azure/sonic-platform-common/pull/106)

#### PDDF advance to SONiC Platform 2.0, BMC
SONiC OS is portable across different network devices with supported ASIC via Switch Abstraction Interface (SAI). These devices primarily differ in the way various device specific hardware components are accessed, and thus require custom device drivers and python plugins. Each platform vendor implements these custom device drivers and plugins. The feature requirement is to support a SONiC platform driver development framework to enable rapid development of custom device drivers and plugins.
<br> **Pull Requests** : [4756](https://github.com/Azure/sonic-buildimage/pull/4756), [940](https://github.com/Azure/sonic-utilities/pull/940), [92](https://github.com/Azure/sonic-platform-common/pull/92), [3387](https://github.com/Azure/sonic-buildimage/pull/3387), [624](https://github.com/Azure/sonic-utilities/pull/624), [62](https://github.com/Azure/sonic-platform-common/pull/62) 

#### Support hardware reboot/reload reason (Streaming Telemetry)
This feature enables sonic streaming telemetry agent to send Reboot-cause information. During the boot, the determine-reboot-cause service ( previously process-reboot-cause) determines the last reboot-cause based on the hardware reboot-cause and the software reboot-cause information and determine-reboot-cause service will save the JSON-formatted last previous reboot cause information to "/host/reboot-cause/history/" with adding timestamp at the end of file name. 
<br> **Pull Requests** : [5562](https://github.com/Azure/sonic-buildimage/pull/5562), [1154](https://github.com/Azure/sonic-utilities/pull/1154) 

#### System health and system LED
System health monitor is intended to monitor both critical services and peripheral device status and leverage system log, system status LED to and CLI command output to indicate the system status.In current SONiC implementation, we already have Monit which is monitoring the critical services status and also have a set of daemons.System health monitoring service will not monitor the critical services or devices directly, it will reuse the result of Monit and PMON daemons to summary the current status and decide the color of the system health LED.
<br> **Pull Requests** : [4835](https://github.com/Azure/sonic-buildimage/pull/4835) & [4829](https://github.com/Azure/sonic-buildimage/pull/4829)

#### Distributed forwarding in a VOQ architecture HLD
This feature provides the implementation of SONiC support for distributed packet forwarding across a set of devices that have a VOQ (Virtual Output Queue) architecture interconnected by an internal fabric. Support for distributed forwarding encompasses the following aspects such as Physical interfaces and VOQs, Logical interfaces such as link aggregation groups (LAGs), The internal interconnection fabric, The packet forwarding data plane, The control plane, both internal (within the devices in the system) and with external devices.
<br> **Pull Requests** : [5283](https://github.com/Azure/sonic-buildimage/pull/5283)

#### Chassis infrastructure, T2 topologies and sample Testcases converted
**Pull Requests** : [2245](https://github.com/Azure/sonic-mgmt/pull/2245), [2417](https://github.com/Azure/sonic-mgmt/pull/2417), [2638](https://github.com/Azure/sonic-mgmt/pull/2638/)







<br>


# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.7.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.7.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Microsoft, Broadcom, DellEMC, Mellanox, Alibaba, Linkedin, Nephos & Aviz. 

<br>



