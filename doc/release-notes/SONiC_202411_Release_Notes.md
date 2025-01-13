# SONiC 202411 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202411](https://github.com/orgs/sonic-net/projects/18/) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202411 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_6.1.94-1  |
| SAI   version             | SAI v1.15.1    |
| FRR                       | 10.0.1   |
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
| Debian version			| Continuous to use Bookworm (Debian version 12)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 6.1.38-4 to 6.1.94-1 for SONiC release.<br>
   Change log: https://cdn.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.1.94

2. Docker is with 24.0.2-1~debian-stretch  <br>
   Change log: https://docs.docker.com/engine/release-notes/24.0/#2402


# Feature List

| Feature| Feature Description | HLD PR / PR tracking |	Quality |
| ------ | ------- | -----|-----|
| ***Add HLD for FRR-SONiC Communication Channel Enhancements*** | This feature introduces a SONiC-specific communication channel between FRR and SONiC.    |  [1620](https://github.com/sonic-net/SONiC/pull/1620)    | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |   
| ***Authentication Manager for PAC*** | This feature implements the authentication manager for PAC like API interface, generic header and makefile and common header files.   | [1853](https://github.com/sonic-net/SONiC/issues/1853)   | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Banner HLD*** | This feature covers the definition, design and implementation of SONiC Banner feature and Banner CLI. |[1361](https://github.com/sonic-net/SONiC/pull/1361)| [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***BBR and Overlay ECMP coexistence with dual ToR*** | This feature adds the logic to give Vnet routes precedence over BGP learnt route. This feature also refactors the test_vnet.py to break out the common code into a library. | [1735](https://github.com/sonic-net/SONiC/issues/1735) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***BMP for monitoring SONiC BGP info*** | This feature is to bring up BMP container on SONiC, which is forked from openbmp project with some code changes, by that we could improve the SONiC debuggability and BGP service monitoring efficiency.    | [1621](https://github.com/sonic-net/SONiC/pull/1621)     | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Broadcom syncd bookworm upgrade*** | This feature implements the migration of platform broadcom docker syncd from bullseye to bookworm | [19712](https://github.com/sonic-net/sonic-buildimage/pull/19712) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Everflow DSCP marking using Metadata*** | This feature implements the High level design of a new table type which can change the outer DSCP of a packet encapsulated by ther ASIC pipeline while preserving the orignal packets inner DSCP value. |  [1743](https://github.com/sonic-net/SONiC/pull/1743) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***HLD for cli sessions feature*** | This feature describes the requirements, architecture and general flow details of serial connection config in SONIC OS based switches. | [1367](https://github.com/sonic-net/SONiC/pull/1367) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Mac Authentication Bypass*** | This feature implements MAB protocol related common header files for generic files and its changes. | [1854](https://github.com/sonic-net/SONiC/issues/1854)   | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Port Access Control Phase 1*** | This feature provides a means of preventing unauthorized access by users to the services offered by a Network. | [1315](https://github.com/sonic-net/SONiC/pull/1315) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Silicon config support for Broadcom yml file and property overwrite*** | This feature gives the details of Per-switching silicon Common config for Broadcom Supported Platforms implementation.   | [1744](https://github.com/sonic-net/SONiC/pull/1744) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Upgrade FRR to version 10.0.1, upgrade libyang2 to 2.1.148.*** | This implements the version update for FRR to version 10.0.1 and libyang2 to 2.1.148.  | [20269](https://github.com/sonic-net/sonic-buildimage/pull/20269)     | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***Upgrade to FRR 10.0.1*** | This implements the version update for FRR to version 10.0.1   | [1565](https://github.com/sonic-net/SONiC/issues/1565)     | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 


Note : The HLD PR's have been updated in ""HLD PR / PR tracking"" coloumn. The code PR's part of the features are mentioned within the HLD PRs. The code PRs not mentioned in HLD PRs are updated in "HLD PR / PR tracking" coloumn along with HLD PRs.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.15.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.15.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Alibaba, AvizNetworks, Broadcom, Cisco, Dell, Micas Networks, Microsoft, NTT, Nvidia & xFlow Research Inc.   

<br> 



