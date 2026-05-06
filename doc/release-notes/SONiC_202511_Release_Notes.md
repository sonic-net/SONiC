# SONiC 202511 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202511](https://github.com/orgs/sonic-net/projects/35/) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202511 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_6.12.41-1  |
| SAI   version             | SAI v1.17.4    |
| FRR                       | 10.3.0   |
| LLDPD                     | 1.0.16-1+deb12u1 |
| TeamD                     | 1.31-1    |
| SNMPD                     | 5.9.4+dfsg |
| Python                    | 3.11.2-6    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.19-1+b1 |
| isc-dhcp                  | 4.4.3-P1  |
| sonic-telemetry           | 1.1    |
| redis-server/ redis-tools | 7.0.15-1~deb12u1   |
| Debian version			| Continuous to use Bookworm (Debian version 12)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 6.1.123 to 6.12.41-1 for SONiC release.<br>
   Change log: https://www.kernel.org/pub/linux/kernel/v6.x/ChangeLog-6.12.41

2. Docker is with 29.2.1-debian-stretch  <br>
   Change log: https://docs.docker.com/engine/release-notes/28/#2821


# Feature List

| Feature| Feature Description | HLD PR / PR tracking |	Quality |
| ------ | ------- | -----|-----|
| ***HLD document for configurable drop counter monitoring*** | This feature adds a persistent drop counter monitoring feature to identify persistent packet drops based on user-defined thresholds.  | [1912](https://github.com/sonic-net/SONiC/pull/1912) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***HLD of SONiC FIPS POST support*** | This feature describes SONiC design for Federal Information Processing Standards (FIPS) 140-3 standard compliance. Especially, the focus of the document is to trigger MACSec Pre-Operational Self-Test (POST) in SONiC and also ensure SONiC’s behavior is compliant to FIPS standard after POST.  | [2034](https://github.com/sonic-net/SONiC/pull/2034) |  [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***ANew DHCPv4 relay design to replace ISC-DHCP*** | This feature provides a high-level design for a new SONiC DHCPv4 relay agent that overcomes the limitations of the existing ISC-DHCP implementation by introducing a modernized architecture, enhanced features, updated configuration model, and clear backward compatibility considerations to support a smooth transition from isc-dhcp.| [1937](https://github.com/sonic-net/SONiC/issues/1937) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***Add support for VLAN interface using OpenConfig YANG*** | This feature adds transformer support for OpenConfig VLAN interfaces and VLAN members (physical and PortChannel). |  [2000](https://github.com/sonic-net/SONiC/pull/2000) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***Enhancement: Upgrade to libyang3*** | This feature upgrades SONiC to the latest stable libyang release (3.12.2) to eliminate legacy issues, remove workarounds, and improve stability and security.|  [22385](https://github.com/sonic-net/sonic-buildimage/issues/22385) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| [testbed_doc] ***Base OS upgrade to Trixie*** | This update upgrades the base OS to Trixie, including core components such as the kernel and Docker daemon, to provide a more modern, stable, and secure operating environment. | [2040](https://github.com/sonic-net/SONiC/issues/2040) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***BMC flows in SONiC*** | This feature introduces foundational support for BMC flows in SONiC using the Redfish standard, including Redfish client integration, BMC IP configuration, new BMC‑related CLI commands, and asynchronous BMC log collection via show techsupport, while remaining OS‑agnostic and defining only the required SONiC interfaces. | [2062](https://github.com/sonic-net/SONiC/pull/2062) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***HLD Add multifpgapci module***  | This feature extends the PDDF framework to support multiple PCIe FPGAs in the system, expanding the current single‑FPGA capability and enabling full multi‑FPGA management within SONiC. | [2006](https://github.com/sonic-net/SONiC/pull/2006) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Single-ASIC VOQ proposal*** | This feature adds support for operating SONiC in VOQ mode on single‑ASIC switch systems, enabling the required architecture and behavior for VOQ‑based operation. | [2008](https://github.com/sonic-net/SONiC/pull/2008) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Enhancement: Make thermalctld polling intervals configurable*** | This feature makes the thermalctld polling intervals configurable, allowing vendors to adjust monitoring frequency based on their specific platform requirements.  | [24035](https://github.com/sonic-net/sonic-buildimage/issues/24035) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Add HLD for Reboot support BlockingMode in SONiC*** | This feature introduces a blocking mode for the reboot script, replacing the current non‑blocking behavior to enable automation systems to reliably determine the success of reboot operations.  | [2016](https://github.com/sonic-net/SONiC/pull/2016) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |


Note : The HLD PR's have been updated in ""HLD PR / PR tracking"" coloumn. The code PR's part of the features are mentioned within the HLD PRs. The code PRs not mentioned in HLD PRs are updated in "HLD PR / PR tracking" coloumn along with HLD PRs.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.16.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.16.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. 

<br> 



