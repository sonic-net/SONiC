# SONiC 202605 Release Notes (Draft)

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202605](https://github.com/orgs/sonic-net/projects/35/) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202605 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | 6.12.41  |
| SAI   version             | 1.7.3.0-1.RC1    |
| FRR                       | 10.5.4   |
| LLDPD                     | 1.0.16-1+deb12u1 |
| TeamD                     | 1.31-1    |
| SNMPD                     | 5.9.3+dfsg |
| Python                    | 3.13.5-2    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.20-1+b1 |
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
| ***Support for OC-YANG target for dial-out telemetry*** | This feature adds support for dial-out telemetry with the OC Yang target.| [558](https://github.com/sonic-net/sonic-gnmi/pull/558) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***Add Multi-ASIC warm-reboot*** | This feature fixes multi-ASIC configurations with all frontend ASICs and no interconnect, with support limited to this specific configuration. | [2153](https://github.com/sonic-net/SONiC/pull/2153) |  [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***Add SED support for Change/Reset SED password*** |This feature describes SED password management in SONiC, including changing and resetting passwords via CLI using the platform API.| [2171](https://github.com/sonic-net/SONiC/pull/2171) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***BMC flows in SONiC*** | This feature introduces foundational BMC support in SONiC using Redfish, including client integration, BMC IP configuration, CLI commands, and asynchronous BMC log collection in show techsupport, with an OS-agnostic interface. |  [2062](https://github.com/sonic-net/SONiC/pull/2062) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/guidelines/SONiC%20feature%20quality%20definition.md)  |
| ***Enhancement: Enable VRF binding for gNMI and Telemetry*** | This feature adds support to bind gNMI and Telemetry processes to a configured VRF.|[504](https://github.com/sonic-net/sonic-gnmi/issues/504) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Added HLD for Dualtor Prefix based Neighbor*** | This feature introduces prefix-based neighbor optimization for DualToR, reducing SAI calls during mux state changes to minimize traffic loss. | [2176](https://github.com/sonic-net/SONiC/pull/2176) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Event and alarm management*** | This feature enhances the event framework with persistent event history support and adds gNMI/REST OpenConfig interfaces for retrieval and subscription. | [22617](https://github.com/sonic-net/sonic-buildimage/pull/22617) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***[Dell] Z9864F initial commit***  | This feature adds support for the Dell Z9864F-TH5 platform, including platform APIs, drivers, build updates, and NPU configuration. | [26001](https://github.com/sonic-net/sonic-buildimage/pull/26001) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Dell S3248T platform support*** | This feature adds support for the Dell S3248T platform with Broadcom ASIC, including required platform integration and SONiC image support. | [22489](https://github.com/sonic-net/sonic-buildimage/pull/22489) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***[Tracking PR] multi-ASIC extended CLI syntax to multi-ASIC*** | This feature adds documentation for namespace-aware show/config commands with usage, TOC entry, and cross-references to related CLI behavior. | [2288](https://github.com/sonic-net/SONiC/pull/2288) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Added Fast-linkup*** |This feature introduces Fast Link-Up in SONiC, enabling faster link recovery by reusing prior EQ parameters with configurable thresholds and capability-based support. | [2170](https://github.com/sonic-net/SONiC/pull/2170) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***CMIS Vendor Specific DOM Extension HLD*** |This feature introduces a generic vendor extension framework for CMIS modules, enabling vendor-specific telemetry integration without changes to common sonic_xcvr code.| [2291](https://github.com/sonic-net/SONiC/pull/2291) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Update fabric HLD with permanent isolate fabric links section*** |This feature clears previous monitoring status and decisions after fabric port link down/up events, unless the link was manually shut down via CLI. | [2085](https://github.com/sonic-net/SONiC/pull/2085) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Add CMIS LPO Enhancement HLD*** |This feature adds an HLD for enhanced LPO EEPROM registers, including additional SI/debug settings and Xcvrd support in SONiC. | [2205](https://github.com/sonic-net/SONiC/pull/2205) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Implement leak detection common components*** |This feature implements leak detection for the SONiC pmon design (#2215), including BMC interactions, DB schema updates, thermal data integration, and CLI enhancements. | [637](https://github.com/sonic-net/sonic-platform-common/pull/637) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Implement leak detection improvements in thermalctld*** |This feature implements leak detection for the SONiC pmon design (#2215), including BMC and Switch-Host interaction, Rack Manager integration, DB updates, thermal data push, and CLI enhancements. | [776](https://github.com/sonic-net/sonic-platform-daemons/pull/776) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Add PORT_PHY_ATTR flex counter support*** |This feature adds support for polling port PHY attributes using flex counters to monitor SerDes-level metrics.| [3957](https://github.com/sonic-net/sonic-swss/pull/3957) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Flex Counter Phase 2 - Port Serdes Attributes*** |This feature adds support for polling port SerDes attributes via flex counters, including configuration handling, DB mappings, and tracking of SerDes-to-port associations. | [4223](https://github.com/sonic-net/sonic-swss/pull/4223) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***PCIe AER printk ratelimiting backport*** |This feature backports AER printk rate limiting to reduce log spam from frequent corrected error reports. | [520](https://github.com/sonic-net/sonic-linux-kernel/pull/520) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Package Arista platform drivers into aspeed image*** |This feature adds Arista platform driver support for the aspeed image, including packaging and build integration. | [27374](https://github.com/sonic-net/sonic-buildimage/pull/27374) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |
| ***Upgrade FRR to version 10.5.1*** |This feature upgrades FRR to version 10.5.1, including submodule updates and patch alignment. | [25839](https://github.com/sonic-net/sonic-buildimage/pull/25839) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md)  |

Note : The HLD PR's have been updated in ""HLD PR / PR tracking"" coloumn. The code PR's part of the features are mentioned within the HLD PRs. The code PRs not mentioned in HLD PRs are updated in "HLD PR / PR tracking" coloumn along with HLD PRs.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.16.1 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.16.1_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. 

<br> 



