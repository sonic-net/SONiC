# SONiC 202311 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202311](https://github.com/orgs/sonic-net/projects/14/views/1) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202311 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_5.10.0-23-2-$(5.10.179)  |
| SAI   version             | SAI v1.13.3    |
| FRR                       | 8.5.1   |
| LLDPD                     | 1.0.16-1+deb12u1 |
| TeamD                     | 1.30-1    |
| SNMPD                     | 5.9+dfsg-4+deb11u1    |
| Python                    | 3.9.2-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.18-3    |
| isc-dhcp                  | 4.4.1-2.3+deb11u2  |
| sonic-telemetry           | 1.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Continuous to use Bullseye (Debian version 11)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 5.10.103-1 to 5.10.136-1 for SONiC release.<br>
   Change log: https://cdn.kernel.org/pub/linux/kernel/v5.x/ChangeLog-5.10.136

2. Docker upgraded from  24.0.2-debian-stretch to 24.0.7-debian-stretch <br>
   Change log: https://docs.docker.com/engine/release-notes/24.0/#2407


# Feature List

| Feature| Feature Description | HLD PR / PR tracking |	Quality |
| ------ | ------- | -----|-----|
| ***[DASH] ACL tags HLD*** | In a DASH SONiC, a service tag represents a group of IP address prefixes from a given service. The controller manages the address prefixes encompassed by the service tag and automatically updates the service tag as addresses change, minimizing the complexity of frequent updates to network security rules. Mapping a prefix to a tag can reduce the repetition of prefixes across different ACL rules and optimize memory usage. | [1427](https://github.com/sonic-net/SONiC/pull/1427) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***AMD-Pensando ELBA SOC support*** | This patchset adds support for AMD-Pensando ELBA SOC. Elba provides a secure, controlled portal to network services, storage, and the data center control plane. This SOC is used in AMD-Pensando PCI Distributed Services Card (DSC).| [322](https://github.com/sonic-net/sonic-linux-kernel/pull/322) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Auto FEC*** | This feature delivers a deterministic approach when FEC and autoneg are configured together which is currently left to vendor implementation. | [1416](https://github.com/sonic-net/SONiC/pull/1416)	 | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Banner HLD*** | This feature covers the definition, design and implementation of SONiC Banner feature and Banner CLI. |[1361](https://github.com/sonic-net/SONiC/pull/1361)| [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***FRR version 8.5.1 Upgrade*** | This feature is achieved with the implementation of new FRR 8.5.1 integration | [15965](https://github.com/sonic-net/sonic-buildimage/pull/15965) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Build improvements changes*** | This feature adds optimization for the SONiC image build by splitting the final build step into two stages. It allows running the first stage in parallel, improving build time. | [1413](https://github.com/sonic-net/SONiC/issues/1413) & [15924](https://github.com/sonic-net/sonic-buildimage/pull/15924) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***CMIS host management - Port signal integrity per speed*** | This feature provides general information about configuring port signal integrity per speed in SONiC.  | [1376](https://github.com/sonic-net/SONiC/issues/1376) & [1455](https://github.com/sonic-net/SONiC/pull/1455) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***CMIS Module Management Enhancement HLD *** | This feature is to enhance host_tx_ready set process to State DB, to have full synchronization between asic and module configuration.  | [1453](https://github.com/sonic-net/SONiC/pull/1453) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Container Hardening*** | This feature implements the container hardening, containing the security hardening requirements and definitions for all containers on top of SONiC | [1364](https://github.com/sonic-net/SONiC/pull/1364) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Create CMIS-custom-SI-settings.md*** | This feature is to apply host defined SI parameters to CMIS supported modules. | [1334](https://github.com/sonic-net/SONiC/pull/1334) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Egress Sflow Enhancement.*** | This feature updates the existing sFlow HLD for egress Sflow support. | [1268](https://github.com/sonic-net/SONiC/pull/1268) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Factory reset*** | This feature implements the support for reset factory feature in Sonic OS. | [1231](https://github.com/sonic-net/SONiC/pull/1231) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Fix containers deployments dependencies on boot/config_reload affecting user experience*** | Currently hostcfgd controls the services based on the feature table. The feature table has a specific field 'has_timer' for the non essential services which needs to be delayed during the reboot flow. This field will be now replaced by new field called "delayed". These services will controlled by hostcfgd. | [1203](https://github.com/sonic-net/SONiC/pull/1203) & [1379](https://github.com/sonic-net/SONiC/issues/1379) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |	
| ***gNMI Master Arbitration*** | For high availability, a system may run multiple replicas of a gNMI client. Among the replicas, only one client should be elected as master and do gNMI operations that mutate any state on the target. However, in the event of a network partition, there can be two or more replicas thinking themselves as master. But if they both call the `Set` RPC, the target may be incorrectly configured by the stale master. Therefore, "Master Arbitration" is needed when multiple clients exist.  | [1285](https://github.com/sonic-net/SONiC/pull/1285) & [1240](https://github.com/sonic-net/SONiC/issues/1240) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |	 
| ***High-level design for Wake-on-LAN feature in SONiC*** | This feature implements the Wake-on-LAN feature design in SONiC. Wake-on-LAN (WoL or WOL) is an Ethernet or Token Ring computer networking standard that allows a computer to be turned on or awakened from sleep mode by a network message.  | [1508](https://github.com/sonic-net/SONiC/pull/1508) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Libvs Port Counter Support*** | In sonic-vs 'show interface counters' is not supported (port counters set to zero). The counter support would be useful for debugging and automation. As part of this feature the basic port counters are fetched from corresponding host interface net stat. | [1398](https://github.com/sonic-net/SONiC/issues/1398) & [1275](https://github.com/sonic-net/sonic-sairedis/pull/1275) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***NAT Bookworm Upgrade*** | This feature updates the fullcone NAT patch in sonic-linux-kernel needs to be updated for Linux 6.1. | [1519](https://github.com/sonic-net/SONiC/issues/1519), [16867](https://github.com/sonic-net/sonic-buildimage/issues/16867) &  [357](https://github.com/sonic-net/sonic-linux-kernel/pull/357) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***NTP: Additional NTP configuration knobs + NTP server provisioning*** | This SONiC Network Time Protocol feature covers Configuring NTP global parameters, Adding/removing new NTP servers, Change the configuration for NTP servers, Show NTP status & Show NTP configuration  | [1296](https://github.com/sonic-net/SONiC/pull/1296) & [1254](https://github.com/sonic-net/SONiC/issues/1254) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***PDDF System Fan Enhancement*** | Current PDDF design supports only 12 individual fans (if 2 fans per tray then total of 6 fantrays). However, some platform have more fans. To support those platforms via PDDF, we added support for more fans in common fan PDDF drivers. | [15956](https://github.com/sonic-net/sonic-buildimage/pull/15956) & [1440](https://github.com/sonic-net/SONiC/issues/1440) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***PDDF support for Ufispace platforms and GPIO extension*** | This feature adds the PDDF support on Ufispace platforms with Broadcom ASIC for S9110-32X, S8901-54XC, S7801-54XS, S6301-56ST | [16017](https://github.com/sonic-net/sonic-buildimage/pull/16017) & [1441](https://github.com/sonic-net/SONiC/issues/1441)| [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Persistent DNS address across reboots*** | With the current implementation dynamic DNS configuration can be received from the DHCP server or static configuration can be set manually by the user. However, SONiC doesn't provide any protection for the static configuration. The configuration that is set by the user can be overwritten with the dynamic configuration at any time. The proposed solution is to add support for static DNS configuration into Config DB. To be able to choose between dynamic and static DNS configurations resolvconf package. | [1380](https://github.com/sonic-net/SONiC/issues/1380), [13834](https://github.com/sonic-net/sonic-buildimage/pull/13834), [14549](https://github.com/sonic-net/sonic-buildimage/pull/14549), [2737](https://github.com/sonic-net/sonic-utilities/pull/2737), [49](https://github.com/sonic-net/sonic-host-services/pull/49), [1322](https://github.com/sonic-net/SONiC/pull/1322), [8436](https://github.com/sonic-net/sonic-mgmt/pull/8436) & [8712](https://github.com/sonic-net/sonic-mgmt/pull/8712) | [GA](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***RADIUS NSS Vulnerability*** | The nss library uses popen to execute useradd and usermod commands. Popen executes using a shell (/bin/sh) which is passed the command string with "-c". This means that if untrusted user input is supplied, unexpected shell escapes can occur. To overcome this, we have suggested to use execle instead of popen to avoid shell escape exploits. | [1399](https://github.com/sonic-net/SONiC/issues/1399) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***[SNMP]: SONiC SNMP Changes to support IPv6*** | The feature captures the changes required to support SNMP over IPv6 for single asic platforms. | [1457](https://github.com/sonic-net/SONiC/pull/1457) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) | 
| ***SSH global config*** | This feature introduces a procedure to configure ssh server global settings. This feature will include 3 configurations in the first phase, but can be extended easily to include additional configurations. | [1169](https://github.com/sonic-net/SONiC/issues/1169), [1075](https://github.com/sonic-net/SONiC/pull/1075) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Sflow 800G Support*** | This feature enhances the current sFlow in sonic, with additional speed due to new ASICs support for 800G. | [1383](https://github.com/sonic-net/SONiC/issues/1383), [2799](https://github.com/sonic-net/sonic-swss/pull/2799) & [2805](https://github.com/sonic-net/sonic-swss/pull/2805) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***TACACS NSS Vulnerability*** | The nss library uses popen to execute useradd and usermod commands. Popen executes using a shell (/bin/sh) which is passed the command string with "-c". This means that if untrusted user input is supplied, unexpected shell escapes can occur. To overcome this, we have suggested to use execle instead of popen to avoid shell escape exploits. | [1464](https://github.com/sonic-net/SONiC/issues/1464) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF: Additional Optimizations for Transformer Infrastructure*** | This feature offers additional optimizational enhancements & bug-fixes for transformer infrastructure.  | [1463](https://github.com/sonic-net/SONiC/issues/1463) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF Infra Enhancement for SONIC-YANG*** | This implements the option to import specific sonic yangs from buildimage sonic-yang-models directory into UMF & CVL enhancement to handle handle singleton tables modeled as a container instead of the usual _LIST syntax | [1397](https://github.com/sonic-net/SONiC/issues/1397) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***UMF Subscription Infra Phase 2*** | This feature implements the  SONiC Telemetry service and Translib infrastructure changes to support gNMI subscriptions and wildcard paths for YANG defined paths. |  [1287](https://github.com/sonic-net/SONiC/pull/1287) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |
| ***Upgrade hsflowd and remove dropmon build flags*** | TBD | [1378](https://github.com/sonic-net/SONiC/issues/1378) | TBD |
| ***Virtual SONiC Network Helper*** | This feature implements vsnet tool to create network of virtual sonic instances | [8459](https://github.com/sonic-net/sonic-mgmt/pull/8459) | [Alpha](https://github.com/sonic-net/SONiC/blob/master/doc/SONiC%20feature%20quality%20definition.md) |


Note : The HLD PR's have been updated in ""HLD PR / PR tracking"" coloumn. The code PR's part of the features are mentioned within the HLD PRs. The code PRs not mentioned in HLD PRs are updated in "HLD PR / PR tracking" coloumn along with HLD PRs.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.13.3 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.13.3_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - AMD, Aviz Networks, Broadcom, Capgemini, Centec, Cisco,  Dell, eBay, Edge core, Google, InMon, Inspur, Marvell, Micas Networks, Microsoft, NTT, Nvidia, Orange, Ufispace, xFlow Research Inc.    

<br> 



