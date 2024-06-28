# SONiC 202405 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202405](https://github.com/orgs/sonic-net/projects/17/) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202405 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_6.1.38-4  |
| SAI   version             | SAI v1.14.0    |
| FRR                       | 8.5.4   |
| LLDPD                     | 1.0.16-1+deb12u1 |
| TeamD                     | 1.31-1    |
| SNMPD                     | 5.9.3+dfsg-2 |
| Python                    | 3.11.2-6    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.19-1+b1 |
| isc-dhcp                  | 4.4.3-P1-2  |
| sonic-telemetry           | 1.1    |
| redis-server/ redis-tools | 7.0.15-1~deb12u1   |
| Debian version			| Migrated to Bookworm (Debian version 12)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 5.10.179-3 to 6.1.38-4 for SONiC release.<br>
   Change log: https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.1.38

2. Docker is with 24.0.2-debian-stretch  <br>
   Change log: https://docs.docker.com/engine/release-notes/24.0/#2402


# Feature List

| Feature| Feature Description | HLD PR / PR tracking |	Quality |
| ------ | ------- | -----|-----|
| ***[LLDP][T2] Advertise Chassis Hostname when present.*** | This feature is for chassis to advertise chassis hostname instead of line card hostname if available to LLDP peers. | [19076](https://github.com/sonic-net/sonic-buildimage/pull/19076) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***[NTP] Fix config template to init default parameters*** | This implements the fix for NTP config generation from the minigraph and save backward compatability | [18736](https://github.com/sonic-net/sonic-buildimage/pull/18736) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***[SubnetDecap] Add subnet decap HLD*** | This feature implements the subnet decapsulation feature on T0 SONiC that allows Netscan to probe VLAN subnet IP addresses.  | [1657](https://github.com/sonic-net/SONiC/pull/1657)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Add details of sff_mgr regarding deterministic bringup for SFF compliant modules*** | This feature adds a new thread sff_mgr under xcvrd to provide deterministic link bringup feature for SFF compliant modules (100G/40G) | [1334](https://github.com/sonic-net/SONiC/pull/1334) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Add HLD for IPv4 port based DHCP server in SONiC*** | This feature implements the design details of ipv4 port based DHCP server in SONiC.  | [1282](https://github.com/sonic-net/SONiC/pull/1282) |  [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Add LDAP HLD*** | This ldap features describes the requirements, architecture and configuration details of ldap feature in switches for SONiC OS build image.  | [1487](https://github.com/sonic-net/SONiC/pull/1487) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Add SRv6 SID L3Adj*** | This feature describes the extensions of SRv6Orch required to support the programming of the L3Adj associated with SRv6 uA, End.X, uDX4, uDX6, End.DX4, and End.DX6 behaviors.     |  [1472](https://github.com/sonic-net/SONiC/pull/1472)     | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Base OS upgrade to Bookworm*** | This feature upgrades SONiC's base image from Debian Bullseye to Debian Bookworm with the notable changes. | [17234](https://github.com/sonic-net/sonic-buildimage/pull/17234)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Bookworm Upgrade LLDP, SNMP subagent, ICCPD, PDE, FRR*** | This feature implements the bookworm upgrade for LLDP, SNMP subagent, ICCPD, PDE, FRR |  [1677](https://github.com/sonic-net/SONiC/issues/1677)     | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***CVL dynamic table field support*** | This implements the CVL relying on 2-key list, to determine the mapping instead it should rely on one key and one non-key leaf. | [1682](https://github.com/sonic-net/SONiC/issues/1682) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***CVL Infra Enhancement*** | This implements the enhancement, fix and optimisation of CVL infra. |  [1680](https://github.com/sonic-net/SONiC/issues/1680) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***CVL singleton table and multi-list table support*** | When dependent target TABLE has multiple lists, if there exists a partial dependency, the loosely hanging LIST was causing sorting issue. This feature implements the fix as retained the last LIST entry instead of first & injected dependency on all target LISTs of the TABLE. | [1681](https://github.com/sonic-net/SONiC/issues/1681)      | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Decrease number of false positive triggers while using  PFC watchdog*** | This feature decreases the number of false positive triggers while using PFC watchdog | [1660](https://github.com/sonic-net/SONiC/pull/1660) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Extend CMIS host management debug capability*** | SONiC show techsupport command provides the ability to collect system dump for debug purpose. Module EEPROM data is important information for PHY issue debugging, but it is not part of show techsupport command. This design will enhance show techsupport command to contain module EEPROM data.   | [1476](https://github.com/sonic-net/SONiC/pull/1476) & [1522](https://github.com/sonic-net/SONiC/pull/1522)   | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Extend CMIS host management to support warmboot and fastboot*** | This feature implements the process on TRANSCEIVER_INFO STATE_DB table on warm start to configure SAI_PORT_ATTR_HOST_TX_SIGNAL_ENABLE on warm boot.And also saves the TRANSCEIVER_INFO/STATUS tables on warm/fast-reboot. | [1663](https://github.com/sonic-net/SONiC/pull/1663) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Go Code format checker and formatter*** | This implements the go code format checker and also formatted the files which don't adhere to go formats. Build will fail if there exists any formatting issue. | [1678](https://github.com/sonic-net/SONiC/issues/1678) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***High-level Design of Storage Monitoring Daemon*** | The goal of the Storage Monitoring Daemon (storagemond) is to provide meaningful metrics for the aforementioned issues and enable streaming telemetry for the attributes so that preventative measures may be triggered in the eventuality of performance degradation.  | [1481](https://github.com/sonic-net/SONiC/pull/1481)   | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***HLD: DHCPv4 - Specify dhcp relay's Gateway explicitly with Primary address.*** | This feature implements the High Level Design of 'Secondary' interfaces of vlan. These secondary interfaces are also excluded in use in dhcpv4 relay. | [1470](https://github.com/sonic-net/SONiC/pull/1470) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***NetScan over VLAN support*** | This feature implements the subnet decap feature HLD to support Netscan over VLAN.  | [1657](https://github.com/sonic-net/SONiC/pull/1657)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***NextHop Group Table Enhancement*** |  This feature implements the changes to handle recursive NHG entries | [1636](https://github.com/sonic-net/SONiC/pull/1636) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***RESTCONF infra enhancement*** | This feature adds the tests for openAPI spec generator, OpenAPI spec generator is enhanced to generate rest-server stubs, this replaces the OpenAPI-generator from community. Also removed the openAPI client generation and added Restconf document generator. Upgraded specs to openAPI 3.0. | [1679](https://github.com/sonic-net/SONiC/issues/1679) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***SAI health monitor and dump generation*** | SAI monitoring feature, describes the behavior when SAI get stuck, NOS notifications and also changes concerning dump, health notification, shutdown and syslog depending on severity of occurred events. | [1533](https://github.com/sonic-net/SONiC/pull/1533) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***SONiC container upgrade to Bookworm (Debian 12)*** | Upgradation on different dockers. | [](https://github.com/sonic-net/SONiC/issues/1541)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***SONiC Debian Upgrade Cadence process improvement*** |      | [1632](https://github.com/sonic-net/SONiC/issues/1632) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Support OpenSSL 3.0 SymCrypt provider and engine for bookworm*** | This feature supports the OpenSSL 3.0 SymCrypt provider and engine for bookworm | [18088](https://github.com/sonic-net/sonic-buildimage/pull/18088) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Test Plan for OSPF and BFD*** | Addition of test plans for OSPF and BFP protocols.  | [](https://github.com/sonic-net/SONiC/issues/1576)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Third party container management using the Sonic Application Framework*** | This feature integrates, TPCM install/update/delete with Application Extensions Framework | [1286](https://github.com/sonic-net/SONiC/pull/1286) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***TLS1.3 Support*** |  Support for TLS 1.3  | [1531](https://github.com/sonic-net/SONiC/issues/1531) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF Config Session Support*** | This feature on config session changes includes config session, locking, transaction size limit. |	[1518](https://github.com/sonic-net/SONiC/pull/1518) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF infra enhancement*** |	This feature describes the high level design for SONiC Telemetry service and Translib infrastructure changes to support gNMI subscriptions and wildcard paths for YANG defined paths. |	[1287](https://github.com/sonic-net/SONiC/pull/1287) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF: OpenConfig YANG support for Physical Interfaces*** |	This feature implements the transformer support for openconfig interfaces.	| [1628](https://github.com/sonic-net/SONiC/pull/1628) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF subscription enhancement*** | This feature helps to verify REST and gNMI get/set operations on the build server itself and also fix the nil check during the subscribe request inside the handleTableXfmrCallback function. | [1705](https://github.com/sonic-net/SONiC/issues/1705) |  [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF: Transformer Infrastructure***	| This feature describes the design for SONiC Telemetry service and Translib infrastructure changes to support gNMI subscriptions and wildcard paths for YANG defined paths. | [1287](https://github.com/sonic-net/SONiC/pull/1287)	| [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Upgrade FRR to 8.5.4*** | This feature upgrades the FRR 8.5.4 to include latest fixes.	| [18669](https://github.com/sonic-net/sonic-buildimage/pull/18669)	| [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Upgrade SWSS/SyncD to debian 12*** | Debian upgrade for SWSS and SyncD | [1670](https://github.com/sonic-net/SONiC/pull/1670) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Weighted-Cost Multi-Path*** | This feature provides general information about Weighted-Cost Multi-Path implementation in SONiC | [1629](https://github.com/sonic-net/SONiC/pull/1629)  | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |


Note : The HLD PR's have been updated in ""HLD PR / PR tracking"" coloumn. The code PR's part of the features are mentioned within the HLD PRs. The code PRs not mentioned in HLD PRs are updated in "HLD PR / PR tracking" coloumn along with HLD PRs.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.14.0 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.14.0_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Alibaba, Arista, AvizNetworks, Broadcom, Capgemini, Centec, Cisco, Dell, eBay, Edge-Core, Google, InMon, Inspur, Intel, Marvell, Micas Networks, Microsoft, NTT, Nvidia, Orange, PLVision & xFlow Research Inc.   

<br> 



