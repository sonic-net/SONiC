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

Branch : https://github.com/sonic-net/sonic-buildimage/tree/202012 <br>
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
| Debian version			| Migrated to Buster (Debian version 10)	|

# Security Updates

1. Kernel upgraded from 4.9.110-3deb9u6 (SONiC Release 201904) to 4.9.168-1+deb9u5 for SONiC release. 
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-4.9.168-1deb9u5
2. Docker upgraded from 18.09.2\~3-0\~debian-stretch to 18.09.8\~3-0\~debian-stretch. 
   Change log: https://docs.docker.com/engine/release-notes/#18098 

# Feature List

#### Consistent ECMP support (fine grain ECMP)
This feature is to modify the behavior of ECMP to achieve fine grained handling of ECMP for a specifically identified prefix and associated next-hops in configuration.
<br> Refer [HLD document](https://github.com/anish-n/SONiC/blob/e5cdb3d9337026a98d6be5d558126926a4e959e4/doc/ecmp/fine_grained_next_hop_hld.md) and below mentioned PR's for more details. 
<br>**Pull Requests** :  [1315](https://github.com/sonic-net/sonic-swss/pull/1315), [623](https://github.com/sonic-net/SONiC/pull/623), [1788](https://github.com/sonic-net/sonic-mgmt/pull/1788), [4985](https://github.com/sonic-net/sonic-buildimage/pull/4985), [374](https://github.com/sonic-net/sonic-swss-common/pull/374), [659](https://github.com/sonic-net/SONiC/pull/659), [1056](https://github.com/sonic-net/sonic-utilities/pull/1056), [5518](https://github.com/sonic-net/sonic-buildimage/pull/5518), [5198](https://github.com/sonic-net/sonic-buildimage/pull/5198), [693](https://github.com/sonic-net/SONiC/pull/693). 

#### Container warm restart (BGP/TeamD/SWSS/SyncD)
The goal of SONiC warm reboot is to be able restart and upgrade SONiC software without impacting the data plane. Warm restart of each individual process/docker is also part of the goal. Except for syncd and database docker, it is desired for all other network applications and dockers to support un-planned warm restart.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/0c177995044316b898fc355456d9b6e8df72b522/doc/warm-reboot/SONiC_Warmboot.md) and below mentioned PR's for more details. 
<br> **Pull Requests** :  [3992](https://github.com/sonic-net/sonic-buildimage/pull/3992), [5233](https://github.com/sonic-net/sonic-buildimage/pull/5233),[5163](https://github.com/sonic-net/sonic-buildimage/pull/5163/files), [5108](https://github.com/sonic-net/sonic-buildimage/pull/5108/files) & [1036](https://github.com/sonic-net/sonic-utilities/pull/1036/files).

#### CoPP Config/Management
During SWSS start, the prebuilt copp.json file is loaded as part of start script swssconfig.sh and written to APP_DB. CoppOrch then translates it to Host trap/policer tables and programmed to SAI. With this enhancement, the CoPP tables shall be loaded to Config_DB instead of APP_DB. The default CoPP json file shall be prebuilt to the image and loaded during initialization. Any Config_DB entries present shall be configured overwriting the default CoPP tables. This also ensures backward compatibility. 
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/fdc7cff16b7f42f1a1b01dd506279e3e9f9269cb/doc/copp/CoPP%20Config%20and%20Management.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [358](https://github.com/sonic-net/sonic-swss-common/pull/358), [1333](https://github.com/sonic-net/sonic-swss/pull/1333), [4861](https://github.com/sonic-net/sonic-buildimage/pull/4861) & [1004](https://github.com/sonic-net/sonic-utilities/pull/1004)

#### Console Support for SONiC (Hardware)
This is a feature to support SONiC for hardware console.
<br> **Pull Requests** :[5571](https://github.com/sonic-net/sonic-buildimage/pull/5571) & [1155](https://github.com/sonic-net/sonic-utilities/pull/1155) 

#### Console Support for SONiC (SSH forwarding)
This feature describes the persistent console configurations to control how to view/connect to a device via serial link.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/126a4f7af8cadd8451b22bd80227c07c11452a63/doc/console/SONiC-Console-Switch-High-Level-Design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [664](https://github.com/sonic-net/SONiC/pull/664), [673](https://github.com/sonic-net/SONiC/pull/673) ,[1117](https://github.com/sonic-net/sonic-utilities/pull/1117) , [1120](https://github.com/sonic-net/sonic-utilities/pull/1120), [1130](https://github.com/sonic-net/sonic-utilities/pull/1130) ,[1136](https://github.com/sonic-net/sonic-utilities/pull/1136) , [1166](https://github.com/sonic-net/sonic-utilities/pull/1166) , [1173](https://github.com/sonic-net/sonic-utilities/pull/1173), [1176](https://github.com/sonic-net/sonic-utilities/pull/1176) , [5438](https://github.com/sonic-net/sonic-buildimage/pull/5438) & [5717](https://github.com/sonic-net/sonic-buildimage/pull/5717).

#### Dynamic headroom calculation
This feature defines the solution on how the headroom is calculated by the well known formula based upon with the cable length and speed as input. Arbitrary cable length will be supported.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/415f19931bccd900ac528b100aafffa6000e82e9/doc/qos/dynamically-headroom-calculation.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1338](https://github.com/sonic-net/sonic-swss/pull/1338), [973](https://github.com/sonic-net/sonic-utilities/pull/973), [4881](https://github.com/sonic-net/sonic-buildimage/pull/4881), [1971](https://github.com/sonic-net/sonic-mgmt/pull/1971), [361](https://github.com/sonic-net/sonic-swss-common/pull/361)

#### Enable synchronous SAI APIs (error handling)
This feature enables the synchronous mode for a closed-loop execution, if SAI APIs are called from the orchagent. In contrast to the previous asynchronous mode which cannot properly handle SAI API failures, the synchronous mode can gracefully handle SAI API failures by conducting the proper actions in orchagent. Therefore, the synchronous mode can substantially improve the reliability of SONiC.
<br> Refer [HLD document](https://github.com/shi-su/SONiC/blob/61762c8e709ead5f8ee7df83facea6ceee9de6f5/doc/synchronous-mode/synchronous-mode-cfg.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [5237](https://github.com/sonic-net/sonic-buildimage/pull/5237) , [650](https://github.com/sonic-net/sonic-buildimage/pull/650) , [652](https://github.com/sonic-net/sonic-buildimage/pull/652) , [653](https://github.com/sonic-net/sonic-buildimage/pull/653), [1094](https://github.com/sonic-net/sonic-utilities/pull/1094) & [5308](https://github.com/sonic-net/sonic-buildimage/pull/5308).

#### EVPN/VXLAN
This feature provides information about the EVPN VXLAN feature implementation based on RFC 7432 BGP EVPN solution over VXLAN tunnels for SONiC, including support for L2 and L3 VPN services, auto discovery of remote VTEPs, auto provisioning of tunnels and VLANs over VXLAN tunnels, control plane MAC learning and ARP suppression for reduced flooding, and support for VM mobility.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/7fbda34ee3315960c164a0c202f39c2ec515cfc3/doc/vxlan/EVPN/EVPN_VXLAN_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [339](https://github.com/sonic-net/sonic-swss-common/pull/339) ,[350](https://github.com/sonic-net/sonic-swss-common/pull/350) , [1264](https://github.com/sonic-net/sonic-swss/pull/1264) , [1266](https://github.com/sonic-net/sonic-swss/pull/1266) , [1318](https://github.com/sonic-net/sonic-swss/pull/1318) , [1267](https://github.com/sonic-net/sonic-swss/pull/1267) & [870](https://github.com/sonic-net/sonic-utilities/pull/870).

#### SONiC entity MIB extensions
The Entity MIB contains several groups of MIB objects: entityPhysical group, entityLogical group and so on. Previously, SONiC only implemented part of the entityPhysical group following RFC2737. Since entityPhysical group is most commonly used, this extension will focus on entityPhysical group and leave other groups for future implementation. The group entityPhysical contains a single table called "entPhysicalTable" to identify the physical components of the system. 
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/0e53548a8f1023d1be2a1dffd62737c7a1b18a2e/doc/snmp/extension-to-physical-entity-mib.md) and below mentioned PR's for more details. 
<br> **Pull Requests** :  [134](https://github.com/sonic-net/sonic-platform-common/pull/134), [102](https://github.com/sonic-net/sonic-platform-daemons/pull/102), [5645](https://github.com/sonic-net/sonic-buildimage/pull/5645), [168](https://github.com/sonic-net/sonic-snmpagent/pull/168)  & [2379](https://github.com/sonic-net/sonic-mgmt/pull/2379)

#### FRR BGP NBI
This feature extends and provides unified configuration and management capability for FRR-BGP features used in SONiC.This enhancement is to load any BGP/route-map configurations from config-DB as well independent of mgmt-framework NBI, the main change here is to add CONFIB_DB entries for FRR management into SONiC, and the ability to apply this config to FRR.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/48e9012c548528b6528745bda9d75b4164e785eb/doc/mgmt/SONiC_Design_Doc_Unified_FRR_Mgmt_Interface.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [5142](https://github.com/sonic-net/sonic-buildimage/pull/5142)

#### Gearbox
This feature is a design change that allows the PHY drivers to be separated from the Switch driver (SAI) by introducing a new driver API for PHYs. This allows diverse, multi-vendor hardware to be more easily supported. This change adds usage capability of this new interface to SONiC.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/gearbox/gearbox_mgr_design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [347](https://github.com/sonic-net/sonic-swss-common/pull/347), [931](https://github.com/sonic-net/sonic-utilities/pull/931), [1321](https://github.com/sonic-net/sonic-swss/pull/1321), [624](https://github.com/sonic-net/sonic-sairedis/pull/624) & [4851](https://github.com/sonic-net/sonic-buildimage/pull/4851).

#### Kubernetes (docker to be controlled by Kubernetes)
This feature deals in depth with kubernetes-support. With this feature, an image could be downloaded from external repositaries and kubernetes does the deployment. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests. This new mode is referred as "kubernetes mode". 

What we implement in this release:
-	The image could be built with kubernetes support 
-	The image carries all kubernetes packages & images required to run as a kubernetes node.
-	The minigraph could provide the IP of your kubernetes master
-	The node upon startup, joins the master
-	The switch add labels to the node, expressing its OS version, versions of various features
-	The cli commands config & show are provided to manage the support

If you have an infrastructure that runs kubernetes master cluster, then you could
-	You could have your build pipeline push docker images to your registry or ACR (Azure Container Registry)
-	For intended updates, publish manifests
-	With node selector labels (optionally)
-	With image pull secrets provided
-	You may create secret to access your repo and make it default across all
<br> Refer [HLD document](https://github.com/renukamanavalan/SONiC/blob/kube_systemd/doc/kubernetes/Kubernetes-support.md) and below mentioned PR's for more details. 
<br> **Pull Requests** :  [4825](https://github.com/sonic-net/sonic-buildimage/pull/4825), [4895](https://github.com/sonic-net/sonic-buildimage/pull/4895), [4926](https://github.com/sonic-net/sonic-buildimage/pull/4926), [4932](https://github.com/sonic-net/sonic-buildimage/pull/4932),  [4959](https://github.com/sonic-net/sonic-buildimage/pull/4959), [4973](https://github.com/sonic-net/sonic-buildimage/pull/4973), [5022](https://github.com/sonic-net/sonic-buildimage/pull/5022), [5113](https://github.com/sonic-net/sonic-buildimage/pull/5113),    [5121](https://github.com/sonic-net/sonic-buildimage/pull/5121), [5122](https://github.com/sonic-net/sonic-buildimage/pull/5122), [5202](https://github.com/sonic-net/sonic-buildimage/pull/5202), [5221](https://github.com/sonic-net/sonic-buildimage/pull/5221),   [5224](https://github.com/sonic-net/sonic-buildimage/pull/5224), [5235](https://github.com/sonic-net/sonic-buildimage/pull/5235), [5316](https://github.com/sonic-net/sonic-buildimage/pull/5316), [5329](https://github.com/sonic-net/sonic-buildimage/pull/5329),  [5357](https://github.com/sonic-net/sonic-buildimage/pull/5357), [5358](https://github.com/sonic-net/sonic-buildimage/pull/5358), [5364](https://github.com/sonic-net/sonic-buildimage/pull/5364),[5418](https://github.com/sonic-net/sonic-buildimage/pull/5418),   [5420](https://github.com/sonic-net/sonic-buildimage/pull/5420), [5436](https://github.com/sonic-net/sonic-buildimage/pull/5436), [5437](https://github.com/sonic-net/sonic-buildimage/pull/5437), [5446](https://github.com/sonic-net/sonic-buildimage/pull/5446),   [5460](https://github.com/sonic-net/sonic-buildimage/pull/5460), [5479](https://github.com/sonic-net/sonic-buildimage/pull/5479), [5503](https://github.com/sonic-net/sonic-buildimage/pull/5503), [5548](https://github.com/sonic-net/sonic-buildimage/pull/5548),  [87](https://github.com/sonic-net/sonic-platform-daemons/pull/87), [81](https://github.com/sonic-net/sonic-py-swsssdk/pull/81), [138](https://github.com/sonic-net/sonic-snmpagent/pull/138), [140](https://github.com/sonic-net/sonic-snmpagent/pull/140), [141](https://github.com/sonic-net/sonic-snmpagent/pull/141),  [145](https://github.com/sonic-net/sonic-snmpagent/pull/145), [154](https://github.com/sonic-net/sonic-snmpagent/pull/154), [155](https://github.com/sonic-net/sonic-snmpagent/pull/155), [158](https://github.com/sonic-net/sonic-snmpagent/pull/158), [161](https://github.com/sonic-net/sonic-snmpagent/pull/161),   [166](https://github.com/sonic-net/sonic-snmpagent/pull/166), [376](https://github.com/sonic-net/sonic-swss-common/pull/376), [856](https://github.com/sonic-net/sonic-utilities/pull/856), [917](https://github.com/sonic-net/sonic-utilities/pull/917),    [978](https://github.com/sonic-net/sonic-utilities/pull/978), [999](https://github.com/sonic-net/sonic-utilities/pull/999), [1005](https://github.com/sonic-net/sonic-utilities/pull/1005), [1006](https://github.com/sonic-net/sonic-utilities/pull/1006),    [1013](https://github.com/sonic-net/sonic-utilities/pull/1013), [1057](https://github.com/sonic-net/sonic-utilities/pull/1057), [1064](https://github.com/sonic-net/sonic-utilities/pull/1064), [1079](https://github.com/sonic-net/sonic-utilities/pull/1079),   [1080](https://github.com/sonic-net/sonic-utilities/pull/1080), [1081](https://github.com/sonic-net/sonic-utilities/pull/1081), [1123](https://github.com/sonic-net/sonic-utilities/pull/1123) & [1137](https://github.com/sonic-net/sonic-utilities/pull/1137) [1127](https://github.com/sonic-net/sonic-utilities/pull/1127)

#### Management Framework (Phase 2)
The SONiC Management Framework provides a unified UI stack, enabling SONiC to be managed through an Industry-standard CLI, RESTCONF and gNMI (using OpenConfig data models). It also offers a rapid development environment for these user-interfaces, based upon automatic code generation from YANG models.

This set of enhancements extends the framework, including (but not limited to) the following additions: -

-	CLI: Usability enhancements, performance enhancements, User-document generation
-	Translib Infrastructure: Much of the UI infrastructure is separated out into a new repo (sonic-mgmt-common), de-coupling it from the UI code (which remains in the sonic-mgmt-framework repo). This allows the sonic-telemetry container (which also uses the infra) to be built and used independently from sonic-mgmt-framework. Other enhancements include support for RPC, YANG versioning, bulk calls (e.g. from gNMI), Authorization, and other code optimizations
-	CVL: This is an infrastructure component to perform UI validations. It is enhanced here to support Dynamic Port Breakout configuration dependency and for improved performance.
-	Transformer: This is an infrastructure component to perform YANG tree to configuration object translations. Enhancements include support for more overloading functions, cascaded operations (for dynamic port breakout) and aliasing
-	REST Server: Enhancements include RBAC, RESTCONF, YANG module discovery, statistics and other optimizations
-	Advance to Python 3.7
-	Use of DBus for communication into the host
-	Build enhancements
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/34cac1aabdc865fc41cbe064a2ab2442645524b1/doc/mgmt/Management%20Framework.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4799](https://github.com/sonic-net/sonic-buildimage/pull/4799),[4765](https://github.com/sonic-net/sonic-buildimage/pull/4765),[4840](https://github.com/sonic-net/sonic-buildimage/pull/4840),[35](https://github.com/sonic-net/sonic-gnmi/pull/35), [38](https://github.com/sonic-net/sonic-gnmi/pull/38),[126](https://github.com/Azure/sonic-build-tools/pull/126), [170](https://github.com/Azure/sonic-build-tools/pull/170), [10](https://github.com/sonic-net/sonic-mgmt-common/pull/10),[11](https://github.com/sonic-net/sonic-mgmt-common/pull/11), [12](https://github.com/sonic-net/sonic-mgmt-common/pull/12), [13](https://github.com/sonic-net/sonic-mgmt-common/pull/13), [15](https://github.com/sonic-net/sonic-mgmt-common/pull/15), [16](https://github.com/sonic-net/sonic-mgmt-common/pull/16), [18](https://github.com/sonic-net/sonic-mgmt-common/pull/18), [19](https://github.com/sonic-net/sonic-mgmt-common/pull/19), [20](https://github.com/sonic-net/sonic-mgmt-common/pull/20), [21](https://github.com/sonic-net/sonic-mgmt-common/pull/21), [22](https://github.com/sonic-net/sonic-mgmt-common/pull/22), [23](https://github.com/sonic-net/sonic-mgmt-common/pull/23), [26](https://github.com/sonic-net/sonic-mgmt-common/pull/26), [27](https://github.com/sonic-net/sonic-mgmt-common/pull/27), [28](https://github.com/sonic-net/sonic-mgmt-common/pull/28), [31](https://github.com/sonic-net/sonic-mgmt-common/pull/31), [32](https://github.com/sonic-net/sonic-mgmt-common/pull/32), [34](https://github.com/sonic-net/sonic-mgmt-common/pull/34), [35](https://github.com/sonic-net/sonic-mgmt-common/pull/35), [50](https://github.com/sonic-net/sonic-mgmt-framework/pull/50), [51](https://github.com/sonic-net/sonic-mgmt-framework/pull/51),[52](https://github.com/sonic-net/sonic-mgmt-framework/pull/52), [53](https://github.com/sonic-net/sonic-mgmt-framework/pull/65), [57](https://github.com/sonic-net/sonic-mgmt-framework/pull/57), [60](https://github.com/sonic-net/sonic-mgmt-framework/pull/60),[65](https://github.com/sonic-net/sonic-mgmt-framework/pull/65), [66](https://github.com/sonic-net/sonic-mgmt-framework/pull/66),  [67](https://github.com/sonic-net/sonic-mgmt-framework/pull/67), [68](https://github.com/sonic-net/sonic-mgmt-framework/pull/68), [69](https://github.com/sonic-net/sonic-mgmt-framework/pull/69),[71](https://github.com/sonic-net/sonic-mgmt-framework/pull/71), [5810](https://github.com/sonic-net/sonic-buildimage/pull/5810),[5920](https://github.com/sonic-net/sonic-buildimage/pull/5920),[72](https://github.com/sonic-net/sonic-mgmt-framework/pull/72), [73](https://github.com/sonic-net/sonic-mgmt-framework/pull/73), [5714](https://github.com/sonic-net/sonic-buildimage/pull/5714),[61](https://github.com/sonic-net/sonic-gnmi/pull/61)

#### Merge common lib for C++ and python (SWSS common lib)
This is a fix for common lib and associated files.
<br> **Pull Requests** : [378](https://github.com/sonic-net/sonic-swss-common/pull/378) 

#### Move from Python2->python3
 This is inline as part of moving all SONiC code from Python 2 (no longer supported) to Python 3.
<br> **Pull Requests** : [5886](https://github.com/sonic-net/sonic-buildimage/pull/5886), [6038](https://github.com/sonic-net/sonic-buildimage/pull/6038), [6162](https://github.com/sonic-net/sonic-buildimage/pull/6162), [6176](https://github.com/sonic-net/sonic-buildimage/pull/6176), [1542](https://github.com/sonic-net/sonic-swss/pull/1542)

#### Multi-ASIC 202006
This feature is for a platform with more than one ASIC present on it, which is defined as a multi ASIC platform. SONiC so far supports platforms with single ASIC, we are enhancing SONiC to support multiple ASIC platforms.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/ebe4f4b695af5d2dbd23756d3cff03aef0a0c880/doc/multi_asic/SONiC_multi_asic_hld.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4825](https://github.com/sonic-net/sonic-buildimage/pull/4825), [4895](https://github.com/sonic-net/sonic-buildimage/pull/4895), [4926](https://github.com/sonic-net/sonic-buildimage/pull/4926), [4932](https://github.com/sonic-net/sonic-buildimage/pull/4932), [4959](https://github.com/sonic-net/sonic-buildimage/pull/4959), [4973](https://github.com/sonic-net/sonic-buildimage/pull/4973), [5022](https://github.com/sonic-net/sonic-buildimage/pull/5022), [5113](https://github.com/sonic-net/sonic-buildimage/pull/5113), [5121](https://github.com/sonic-net/sonic-buildimage/pull/5121), [5122](https://github.com/sonic-net/sonic-buildimage/pull/5122), [5202](https://github.com/sonic-net/sonic-buildimage/pull/5202), [5221](https://github.com/sonic-net/sonic-buildimage/pull/5221), [5224](https://github.com/sonic-net/sonic-buildimage/pull/5224), [5235](https://github.com/sonic-net/sonic-buildimage/pull/5235), [5316](https://github.com/sonic-net/sonic-buildimage/pull/5316), [5329](https://github.com/sonic-net/sonic-buildimage/pull/5329), [5357](https://github.com/sonic-net/sonic-buildimage/pull/5357), [5358](https://github.com/sonic-net/sonic-buildimage/pull/5358), [5364](https://github.com/sonic-net/sonic-buildimage/pull/5364), [5418](https://github.com/sonic-net/sonic-buildimage/pull/5418), [5420](https://github.com/sonic-net/sonic-buildimage/pull/5420), [5436](https://github.com/sonic-net/sonic-buildimage/pull/5436), [5437](https://github.com/sonic-net/sonic-buildimage/pull/5437), [5446](https://github.com/sonic-net/sonic-buildimage/pull/5446), [5460](https://github.com/sonic-net/sonic-buildimage/pull/5460), [5479](https://github.com/sonic-net/sonic-buildimage/pull/5479), [5503](https://github.com/sonic-net/sonic-buildimage/pull/5503), [5548](https://github.com/sonic-net/sonic-buildimage/pull/5548), [87](https://github.com/sonic-net/sonic-platform-daemons/pull/87), [81](https://github.com/sonic-net/sonic-py-swsssdk/pull/81), [138](https://github.com/sonic-net/sonic-snmpagent/pull/138), [140](https://github.com/sonic-net/sonic-snmpagent/pull/140), [141](https://github.com/sonic-net/sonic-snmpagent/pull/141), [145](https://github.com/sonic-net/sonic-snmpagent/pull/145), [154](https://github.com/sonic-net/sonic-snmpagent/pull/154), [155](https://github.com/sonic-net/sonic-snmpagent/pull/155), [158](https://github.com/sonic-net/sonic-snmpagent/pull/158), [161](https://github.com/sonic-net/sonic-snmpagent/pull/161), [166](https://github.com/sonic-net/sonic-snmpagent/pull/166), [376](https://github.com/sonic-net/sonic-swss-common/pull/376), [856](https://github.com/sonic-net/sonic-utilities/pull/856), [917](https://github.com/sonic-net/sonic-utilities/pull/917), [978](https://github.com/sonic-net/sonic-utilities/pull/978), [999](https://github.com/sonic-net/sonic-utilities/pull/999), [1005](https://github.com/sonic-net/sonic-utilities/pull/1005), [1006](https://github.com/sonic-net/sonic-utilities/pull/1006), [1013](https://github.com/sonic-net/sonic-utilities/pull/1013), [1057](https://github.com/sonic-net/sonic-utilities/pull/1057), [1064](https://github.com/sonic-net/sonic-utilities/pull/1064), [1079](https://github.com/sonic-net/sonic-utilities/pull/1079), [1080](https://github.com/sonic-net/sonic-utilities/pull/1080), [1081](https://github.com/sonic-net/sonic-utilities/pull/1081), [1123](https://github.com/sonic-net/sonic-utilities/pull/1123), [1137](https://github.com/sonic-net/sonic-utilities/pull/1137) & [1127](https://github.com/sonic-net/sonic-utilities/pull/1127)

#### Multi-DB enhancement-Part 2
This feature is for restoring each database with all data before warmboot and then flush unused data in each instance.Restore needs to be done in database docker since we need to know the database_config.json in new version. Need to copy all data rdb file into each instance restoration location and then flush unused database. All other logic remains the same as before.
<br>**Pull Requests** : [5773](https://github.com/sonic-net/sonic-buildimage/pull/5773) & [1205](https://github.com/sonic-net/sonic-utilities/pull/1205)

#### ONIE FW tools
SONiC FW utility uses platform API to interact with the various platform components. SONiC FW utility extends to support for the automatic firmware update based on "platform_components.json" under platform directory and next reboot option which is passed as a option for fwutil update all fw command. SONiC FW utility also extends to support for the automatic firmware update with a custom firmware package that can include any firmware update tool and the firmware update tool will be used for the firmware update if it's specified in the "platform_components.json".
<br> Refer [HLD document](https://github.com/sujinmkang/SONiC/blob/357485991d768a9fa78873bb083e3979fbc5cf71/doc/fwutil/fwutil.md) and below mentioned PR's for more details. 
<br>**Pull Requests** : [1165](https://github.com/sonic-net/sonic-utilities/pull/1165), [106](https://github.com/sonic-net/sonic-platform-common/pull/106)

#### PDDF advance to SONiC Platform 2.0, BMC
PDDF is a rapid platform development environment for SONiC, enabling new platforms to be quickly integrated into the SONiC eco-system by automating much of the routine development using simple description files. It supports both the SONiC Platform 1.0 and 2.0 designs (though 2.0 is preferred). Also supports BMC.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/platform/brcm_pdk_pddf.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4756](https://github.com/sonic-net/sonic-buildimage/pull/4756), [940](https://github.com/sonic-net/sonic-utilities/pull/940), [92](https://github.com/sonic-net/sonic-platform-common/pull/92), [3387](https://github.com/sonic-net/sonic-buildimage/pull/3387), [624](https://github.com/sonic-net/sonic-utilities/pull/624), [62](https://github.com/sonic-net/sonic-platform-common/pull/62) 

#### Support hardware reboot/reload reason (Streaming Telemetry)
This feature enables SONiC streaming telemetry agent to send Reboot-cause information. During the boot, the determine-reboot-cause service ( previously process-reboot-cause) determines the last reboot-cause, based on the hardware reboot-cause. And the software reboot-cause information and determine-reboot-cause service will save the JSON-formatted last previous reboot cause. Information is "/host/reboot-cause/history/" by adding timestamp at the end of file name. 
<br> Refer [HLD document](https://github.com/sujinmkang/SONiC/blob/6ed19e88c6f7aac74640d3d343210d840af70a23/doc/system-telemetry/reboot-cause.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [5562](https://github.com/sonic-net/sonic-buildimage/pull/5562), [1154](https://github.com/sonic-net/sonic-utilities/pull/1154), [5933](https://github.com/sonic-net/sonic-buildimage/pull/5933) & [1210](https://github.com/sonic-net/sonic-utilities/pull/1210)

#### System health and system LED
System health monitor is intended to monitor both critical services and peripheral device status and leverage system log, system status LED to and CLI command output to indicate the system status.In current SONiC implementation, we already have Monit which is monitoring the critical services status and also have a set of daemons.System health monitoring service will not monitor the critical services or devices directly, it will reuse the result of Monit and PMON daemons to summarize the current status and decide the color of the system health LED.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-health-HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4835](https://github.com/sonic-net/sonic-buildimage/pull/4835) & [4829](https://github.com/sonic-net/sonic-buildimage/pull/4829)

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.7.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.7.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Microsoft, Broadcom, DellEMC, Nvidia, Alibaba, Linkedin, Nephos & Aviz. 

<br>



