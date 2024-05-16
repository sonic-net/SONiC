# SONiC 202305 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202305](https://github.com/orgs/sonic-net/projects/8) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202305 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_5.10.0-18-2-$(5.10.136)  |
| SAI   version             | SAI v1.12.0    |
| FRR                       | 8.2.2   |
| LLDPD                     | 1.0.4-1    |
| TeamD                     | 1.30-1    |
| SNMPD                     | 5.9+dfsg-4+deb11u1    |
| Python                    | 3.9.2-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.18-3    |
| isc-dhcp                  | 4.4.1-2.3   |
| sonic-telemetry           | 1.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Continuous to use Bullseye (Debian version 11)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 5.10.103-1 to 5.10.136-1 for SONiC release.<br>
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-5.10.136-1

2. Docker upgraded from  20.10.22-debian-stretch. to 24.0.2-debian-stretch <br>
   Change log: https://docs.docker.com/engine/release-notes/24.0/#201022


# Feature List

| Feature| Feature Description | HLD PR / PR tracking |	Quality |
| ------ | ------- | -----|-----|
| ***ACL keys for matching BTH_opcode and AETH_syndrome*** | This feature deals with ACL key BTH_OPCODE and AETH_SYNDROME | [1247](https://github.com/sonic-net/SONiC/issues/1247), [13340](https://github.com/sonic-net/sonic-buildimage/pull/13340) & [2617](https://github.com/sonic-net/sonic-swss/pull/2617) | NA* |
| ***Auto tech support w/orchagent abort case*** | It is highly likely that by the time auto-techsupport collects saisdkdump, syncd might have been restarted or in the process of restarting. In either case, we'd be loosing the saisdkdump information before restart which will contain useful information for triaging. Thus, a special handling is needed for the core dumps generated from swss container which is handled in this feature enhancement. | [1175](https://github.com/sonic-net/SONiC/issues/1175) , [1212](https://github.com/sonic-net/SONiC/pull/1212), [2644](https://github.com/sonic-net/sonic-swss/pull/2644), [1198](https://github.com/sonic-net/sonic-sairedis/pull/1198), [2633](https://github.com/sonic-net/sonic-utilities/pull/2633) & [13533](https://github.com/sonic-net/sonic-buildimage/pull/13533)  | NA* |
| ***Build Time Improvement Version Caching Support*** | This features enhances the build time improvement phase 2 - version caching support for python and wget  | [1177](https://github.com/sonic-net/SONiC/issues/1177), [942](https://github.com/sonic-net/SONiC/pull/942), [10352](https://github.com/sonic-net/sonic-buildimage/pull/10352), [12000](https://github.com/sonic-net/sonic-buildimage/pull/12000), [12001](https://github.com/sonic-net/sonic-uildimage/pull/12001), [12005](https://github.com/sonic-net/sonic-buildimage/pull/12005), [14612](https://github.com/sonic-et/sonic-buildimage/pull/14612) & [14613](https://github.com/sonic-net/sonic-buildimage/pull/14613)  | NA* |
| ***Chassis - execute Line card cmds from Sup remotely*** | This feature not a HLD PR but issue for release tracking purpose.  | [2701](https://github.com/sonic-net/sonic-utilities/pull/2701) | NA* |
| ***Collecting dump during SAI failure*** | This feature is to describe the flow to collect useful dumps during SAI failures. | [1212](https://github.com/sonic-net/SONiC/pull/1212), [2644](https://github.com/sonic-net/sonic-swss/pull/2644), [1198](https://github.com/sonic-net/sonic-sairedis/pull/1198), [2633](https://github.com/sonic-net/sonic-utilities/pull/2633) & [13533](https://github.com/sonic-net/sonic-buildimage/pull/13533)  | NA* |
| ***Config Reload Enhancement*** | This feature enhances config reload to sequence the services and faster system initialization. | [1203](https://github.com/sonic-net/SONiC/pull/1203), [45](https://github.com/sonic-net/sonic-host-services/pull/45), [2693](https://github.com/sonic-net/sonic-utilities/pull/2693), [13969](https://github.com/sonic-net/sonic-buildimage/pull/13969) & [7558](https://github.com/sonic-net/sonic-mgmt/pull/7558) | NA* |
| ***Docker migration to Bullseye*** | Docker migration to Bullseye | [1242](https://github.com/sonic-net/SONiC/issues/1242) | NA* |
| ***FIB Suppress Announcements of Routes Not Installed in HW*** | This feature describes a feedback mechanism that allows BGP not to advertise routes that haven't been programmed yet. | [1103](https://github.com/sonic-net/SONiC/pull/1103), [2492](https://github.com/sonic-net/sonic-swss/pull/2492), [708](https://github.com/sonic-net/sonic-swss-common/pull/708), [2511](https://github.com/sonic-net/sonic-swss/pull/2511), [2512](https://github.com/sonic-net/sonic-swss/pull/2512), [2495](https://github.com/sonic-net/sonic-utilities/pull/2495), [12852](https://github.com/sonic-net/sonic-buildimage/pull/12852), [12853](https://github.com/sonic-net/sonic-buildimage/pull/12853), [2551](https://github.com/sonic-net/sonic-swss/pull/2551), [2531](https://github.com/sonic-net/sonic-utilities/pull/2531), [7475](https://github.com/sonic-net/sonic-mgmt/pull/7475) & [7430](https://github.com/sonic-net/sonic-mgmt/pull/7430) | NA* |
| ***MDIO IPC Client Library*** | This feature is an extention based on earlier HLD merged last year for add MDIO IPC Client library support. | [1230](https://github.com/sonic-net/sonic-sairedis/pull/1230) | NA* |
| ***PDDF FPGA Device Support*** | This feature is to enhance PDDF framework to support PCIe based FPGA devices and I2C based FPGA devices. | [1232](https://github.com/sonic-net/SONiC/pull/1232), [13475](https://github.com/sonic-net/sonic-buildimage/pull/13475), [13476](https://github.com/sonic-net/sonic-buildimage/pull/13476), [13477](https://github.com/sonic-net/sonic-buildimage/pull/13477) & [13474](https://github.com/sonic-net/sonic-buildimage/pull/13474) | NA* |
| ***PDDF S3IP Compliant SysFS Path Support*** | This feature is to enhance PDDF framework to generate or map SysFS as per S3IP spec | [1294](https://github.com/sonic-net/SONiC/pull/1294), [15073](https://github.com/sonic-net/sonic-buildimage/pull/15073), [15074](https://github.com/sonic-net/sonic-buildimage/pull/15074) & [15075](https://github.com/sonic-net/sonic-buildimage/pull/15075) | NA* |
| ***PINS Generic SAI Extensions resource monitoring support*** | Critical resource monitoring for dyNA*mic PINS Generic SAI Extensions objects. | [1205](https://github.com/sonic-net/SONiC/issues/1205), [1243](https://github.com/sonic-net/SONiC/pull/1243) & [2649](https://github.com/sonic-net/sonic-swss/pull/2649) | NA* |
| ***Port breakout feature with CMIS eNA*bled*** | Port breakout feature workflows is updated with xcvrd CMIS eNA*bled for QSFP-DD optical modules. Xcvrd (transceiver daemon) running as part of PMON docker container, detects optical module (transceiver) presence. If transceiver is found as QSFP-DD, it initiates and orchestrates entire CMIS FSM until module ready state.   | [1290](https://github.com/sonic-net/SONiC/pull/1290)  | NA* |
| ***Preserve CoPP table during fastboot*** | This feature is on preserving the contents of the CoPP (Sonic Control Plane Policing) tables during reboot for faster LAG creation in order to improve fast-reboot's dataplane downtime. | [1107](https://github.com/sonic-net/SONiC/pull/1107), [2548](https://github.com/sonic-net/sonic-swss/pull/2548) & [2524](https://github.com/sonic-net/sonic-utilities/pull/2524) | NA* |
| ***Reproducible SONiC web server population script*** | The file Server population script is a complementary utility for “SONiC reproducible build” and suppose to ease the process of downloading the web packages from an exterNA*l file storage and uploading them to trusted file storage.  | [976](https://github.com/sonic-net/SONiC/pull/976) & [13545](https://github.com/sonic-net/sonic-buildimage/pull/13545) | NA* |
| ***REST Server DoS Attack Security Fix*** | This feature minimize the malicious traffic to the REST server which causes log flooding. These logs can rapidly fill the syslog. During tests, more than 1.5 MB of these messages were written per minute of DoS attack. This could be used to force log rotation, concealing earlier malicious activity from logs. It could also cause a system outage by filling up the disk.  | [13576](https://github.com/sonic-net/sonic-buildimage/issues/13576) | NA* |
| ***rsyslog enhancements*** | This feature adds the functionality to configure remote syslog servers: protocol, filter, trap severity level and update global syslog configuration: trap severity kevel, message format. | [1218](https://github.com/sonic-net/SONiC/pull/1218), [15897](https://github.com/sonic-net/sonic-buildimage/pull/15897), [2947](https://github.com/sonic-net/sonic-utilities/pull/2947), [14513](https://github.com/sonic-net/sonic-buildimage/pull/14513), [8668](https://github.com/sonic-net/sonic-mgmt/pull/8668), [2843](https://github.com/sonic-net/sonic-utilities/pull/2843), [53](https://github.com/sonic-net/sonic-host-services/pull/53) & [771](https://github.com/sonic-net/sonic-swss-common/pull/771)  | NA*  |
| ***SONiC YANG RADIUS Server and RADIUS table*** | This feature adds the Radius SONiC YANG support | [12749](https://github.com/sonic-net/sonic-buildimage/pull/12749)  | NA* |
| ***SONiC YANG Support for IPv6 Link Local*** | This feature adds the SONiC YANG Support for IPv6 Link Local. | [14757](https://github.com/sonic-net/sonic-buildimage/pull/14757)  | NA* |
| ***Standalone local clock setting*** | This feature Provides the interface for setting time and time zone for switches that are not connected to NTP | [1171](https://github.com/sonic-net/SONiC/issues/1171), [14651](https://github.com/sonic-net/sonic-buildimage/pull/14651), [2793](https://github.com/sonic-net/sonic-utilities/pull/2793) & [57](https://github.com/sonic-net/sonic-host-services/pull/57) | NA* |
| ***Static Route BFD HLD document*** | This feature implements the BfdRouteMgr design to monitor static route nexthop reachability and update static route based on BFD session state. | [1216](https://github.com/sonic-net/SONiC/pull/1216), [13789](https://github.com/sonic-net/sonic-buildimage/pull/13789), [13764](https://github.com/sonic-net/sonic-buildimage/pull/13764) &  [2769](https://github.com/sonic-net/sonic-swss/pull/2769)  | NA* |
| ***Switch Port Modes and VLAN CLI Enhancement*** | This feature is for Switchport modes and enhancements to VLAN CLI. | [912](https://github.com/sonic-net/SONiC/pull/912), [2419](https://github.com/sonic-net/sonic-utilities/pull/2419), [13580](https://github.com/sonic-net/sonic-buildimage/pull/13580) & [7625](https://github.com/sonic-net/sonic-mgmt/pull/7625)  | NA* |
| ***UMF Subscription Infra Phase 1*** | This feature adds UMF subscription support. Subscription Common App changes - Changes in the Common App to return YGOT object instead of JSON. | [1287](https://github.com/sonic-net/SONiC/pull/1287), [67](https://github.com/sonic-net/sonic-mgmt-common/pull/67), [70](https://github.com/sonic-net/sonic-mgmt-common/pull/70), [72](https://github.com/sonic-net/sonic-mgmt-common/pull/72), [73](https://github.com/sonic-net/sonic-mgmt-common/pull/73), [74](https://github.com/sonic-net/sonic-mgmt-common/pull/74),  [76](https://github.com/sonic-net/sonic-mgmt-common/pull/76), [78](https://github.com/sonic-net/sonic-mgmt-common/pull/78),  [79](https://github.com/sonic-net/sonic-mgmt-common/pull/79), [80](https://github.com/sonic-net/sonic-mgmt-common/pull/80), [81](https://github.com/sonic-net/sonic-mgmt-common/pull/81), [82](https://github.com/sonic-net/sonic-mgmt-common/pull/82), [84](https://github.com/sonic-net/sonic-mgmt-common/pull/84), [86](https://github.com/sonic-net/sonic-mgmt-common/pull/86), [90](https://github.com/sonic-net/sonic-mgmt-common/pull/90), [103](https://github.com/sonic-net/sonic-gnmi/pull/103) & [112](https://github.com/sonic-net/sonic-gnmi/pull/112) | NA* |
| ***UMF Transformer Enhancements and Optimization*** | This feature is for Transformer infrastructure -- memory, CRUD/GET operation optimizations, UT. This is a dependency for UMF Subscription support being contributed by Broadcom. This entry was opened to account for Dell's portion of the contribution toward UMF Subscription; it uses the same parent PR as the UMF Subscription Infra [#1191](https://github.com/sonic-net/SONiC/issues/1191) project. | [1330](https://github.com/sonic-net/SONiC/issues/1330), [79](https://github.com/sonic-net/sonic-mgmt-common/pull/79), [80](https://github.com/sonic-net/sonic-mgmt-common/pull/80) & [81](https://github.com/sonic-net/sonic-mgmt-common/pull/81),  | NA* | 
| ***V4/V6 L3 ACL optimization*** | Currently SONiC uses separate ACL tables for L3 and L3v6 ACLs. In some ASICs, if a user wants both v4 and v6 rules, they would end up using two hardware ACL tables instead of one.  The proposal is to give the operator an ability to configure  L3 and L3V6 ACLs in the same hardware ACL Table wherever the underlying platform supports it. The proposed solution supports this without the operator having to change his/her existing ACL configuration in CONFIG_DB.  A similar approach has been taken in the community for Mirror ACL tables earlier. This proposal extends this solution to L3 ACLs. | [1220](https://github.com/sonic-net/SONiC/issues/1220), [1267](https://github.com/sonic-net/SONiC/pull/1267), [2735](https://github.com/sonic-net/sonic-swss/pull/2735), [2794](https://github.com/sonic-net/sonic-utilities/pull/2794) &  [14803](https://github.com/sonic-net/sonic-buildimage/pull/14803)  | NA* |


# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.12.0 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.12.0_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - AvizNetworks, Broadcom, Celestica, Cisco, Dell, Edge-core, Google, Innovium, Intel, Marvell, Microsoft, Nvidia, xFlow Research Inc.    

<br> 


NA* - Not Applicable
