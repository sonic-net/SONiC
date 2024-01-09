# SONiC 202205 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC [202205](https://github.com/Azure/SONiC/wiki/Release-Progress-Tracking-202205) release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [Known Issues](#Known-Issues)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202205 <br> 
Image  : https://sonic-build.azurewebsites.net/ui/sonic/pipelines  (Example - Image for Broadcom based platforms is [here](https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds/51255/artifacts/98637?branchName=master&artifactName=sonic-buildimage.broadcom))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_5.10.0-12-2-$(5.10.103-1)  |
| SAI   version             | SAI v1.10.2    |
| FRR                       | 8.2.2   |
| LLDPD                     | 1.0.4-1    |
| TeamD                     | 1.28-1    |
| SNMPD                     | 5.9+dfsg-3+b1    |
| Python                    | 3.9.2-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.17-2~bpo9+1    |
| isc-dhcp                  | 4.4.1-2   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Continues to use Bullseye (Debian version 11)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 5.10.46-4 to 5.10.103-1 for SONiC release.<br>
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-5.10.103-1

2. Docker upgraded from  20.10.7-debian-stretch. to 20.10.17-debian-stretch.<br>
   Change log: https://docs.docker.com/engine/release-notes/#201017


# Feature List


#### Active Active ToRs
The feature implements Link manager and warm reboot support for active-active dual ToRs. Active-active dual ToR link manager is an evolution of active-standby dual ToR link manager. Both ToRs are expected to handle traffic in normal scenarios. For consistency, we will keep using the term "standby" to refer inactive links or ToRs. 

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/dualtor/active_active_hld.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [1005](https://github.com/sonic-net/SONiC/pull/1005), [64](https://github.com/sonic-net/sonic-linkmgrd/pull/64), [248](https://github.com/sonic-net/sonic-platform-daemons/pull/248), [5413](https://github.com/sonic-net/sonic-mgmt/pull/5413) & [627](https://github.com/sonic-net/sonic-swss-common/pull/627)


#### Add SAI version check to SONiC build system
SONiC is not desinged to work in backward compatibility with older vendor SAI implementations. SAI headers that SONiC's synd daemon is compiled against are taken from OCP SAI repository. So is taken from sonic-buildimage vendor's directory. This leads to a conflict that sometimes SAI in sonic-sairedis repository is updated but vendor SAI in sonic-buildimage is not. This implementation sorts out this conflicts.

Refer below mentioned PR for more details. 
<br>  **Pull Requests** : [935](https://github.com/sonic-net/SONiC/pull/935)


#### Add system date row to ‘show version’
This change implements the addition of current date attribute to the "show version" output that includes the current date and hour on the switch.

Refer below mentioned PR for more details. 
<br>  **Pull Requests** :  [2086](https://github.com/sonic-net/sonic-utilities/pull/2086)


#### Added fan_drawer class support in PDDF
This enhancement impliments the changes to attach the PSU related thermal sensors in the PSU instance. This is acheieved by adding a common class pddf_fan_drawer.py. This class uses the PDDF JSON to fetch the platform specific data. previously, the fan_drawer support was missing in PDDF common platform APIs. This resulted in 'thermalctld' not working and 'show platform fan' and 'show platfomr temperature' commands not working. As _thermal_list array inside PSU class was not initialized. 

Refer below mentioned PR for more details. 
<br>  **Pull Requests** : [10213](https://github.com/sonic-net/sonic-buildimage/pull/10213)


#### Align crmorch with sai_object_type_get_availability
This feature Will not require a new SAI API, but vendors will have to implement this API for using this functionality


Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [2098](https://github.com/sonic-net/sonic-swss/pull/2098)


#### CMIS Diagnostics
This feature implements SONIC QSFPDD CMIS support to provide an unified common SFP parser for the QSFPDD transceivers. Enhance the pmon#xcvrd for the QSFPDD application initialization sequence and enhance the pmon#xcvrd for the QSFPDD diagnostics loopback controls

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/cmis-init.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** :  [876](https://github.com/sonic-net/SONiC/pull/876), [219](https://github.com/sonic-net/sonic-platform-common/pull/219) & [217](https://github.com/sonic-net/sonic-platform-daemons/pull/217)


#### 400G ZR support 
The scope of this feature is to develop APIs for both CMIS and C-CMIS to support 400G ZR modules on SONiC.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/platform_api/CMIS_and_C-CMIS_support_for_ZR.md) and below mentioned PR's for more details.
<br>  **Pull Requests** : [769](https://github.com/sonic-net/SONiC/pull/769), [1076](https://github.com/sonic-net/SONiC/pull/1076)


#### Command for showing specific MAC from DB
This feature adds more options to filter output in show mac and fdbshow command. Introduced options for filter by address and filter by type.Added one more option to display only count.And also introduced show command to display fdb aging time in the switch.

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** :  [1982](https://github.com/sonic-net/sonic-utilities/pull/1982)


#### Deterministic interface Link bring-up
This feature impliments the determistic approach for Interface link bring-up sequence for all interfaces types i.e. below sequence to be followed:

- Initialize and enable NPU Tx and Rx path
- For system with 'External' PHY: Initialize and enable PHY Tx and Rx on both line and host sides; ensure host side link is up
- Then only perform optics data path initialization/activation/Tx enable (for CMIS complaint optical modules) and Tx enable (for SFF complaint optical modules)

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/sfp-cmis/Interface-Link-bring-up-sequence.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [916](https://github.com/sonic-net/SONiC/pull/916), [254](https://github.com/Azure/sonic-platform-daemons/pull/254) & [2277](https://github.com/Azure/sonic-swss/pull/2277)


#### DSCP/TC remapping for tunnel traffic
The current QoS map architecture allows for port-based selection of each QoS map. However, we are not able to override the port-based QoS map for tunnel traffic. This design proposes a method to remapping DSCP and TC for tunnel traffic.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/qos/tunnel_dscp_remapping.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [950](https://github.com/sonic-net/SONiC/pull/950), [10176](https://github.com/sonic-net/sonic-buildimage/pull/10176), [2087](https://github.com/sonic-net/sonic-utilities/pull/2087), [1451](https://github.com/opencomputeproject/SAI/pull/1451), [1023](https://github.com/sonic-net/sonic-sairedis/pull/1023), [10417](https://github.com/sonic-net/sonic-buildimage/pull/10417), [10444](https://github.com/sonic-net/sonic-buildimage/pull/10444), [600](https://github.com/sonic-net/sonic-swss-common/pull/600), [2171](https://github.com/sonic-net/sonic-swss/pull/2171), [2190](https://github.com/sonic-net/sonic-swss/pull/2190), [10496](https://github.com/sonic-net/sonic-buildimage/pull/10496), [10565](https://github.com/sonic-net/sonic-buildimage/pull/10565) & [10936](https://github.com/sonic-net/sonic-buildimage/pull/10936)


#### Dynamic policy based hashing (edit flow)
This feature implements the PBH to use ACL engine which match NVGRE/VxLAN packets and calculates hash based on user-defined rules. Hashing is configured based on inner 5-tuple: IP proto, L4 dst/src port, IPv4/IPv6 dst/src. A custom hashing can be configured for Regular/FG ECMP and LAG.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/pbh/pbh-design.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [909](https://github.com/sonic-net/SONiC/pull/909), [586](https://github.com/sonic-net/sonic-swss-common/pull/586), [2169](https://github.com/sonic-net/sonic-swss/pull/2169), [2093](https://github.com/sonic-net/sonic-utilities/pull/2093) & [5263](https://github.com/sonic-net/sonic-mgmt/pull/5263)


#### Extend auto tech support for memory threshold
Currently, techsupport is run by invoking show techsupport either by orchestration tools or manually. The techsupport dump also collects any core dump files available in the /var/core/ directory. However upon the techsupport invocation be made event-driven based on core dump generation, that would improve the debuggability which is implimented on this enhancement.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/auto_techsupport_and_coredump_mgmt.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [939](https://github.com/sonic-net/SONiC/pull/939), [2116](https://github.com/sonic-net/sonic-utilities/pull/2116) & [10433](https://github.com/sonic-net/sonic-buildimage/pull/10433)


#### Fast-reboot flow improvements
The feature SONiC fast-reboot is to be able to restart and upgrade SONiC software with a data plane disruption less than 30 seconds and control plane less than 90 seconds. 

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/fast-reboot/Fast-reboot_Flow_Improvements_HLD.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [980](https://github.com/sonic-net/SONiC/pull/980), [11594](https://github.com/sonic-net/sonic-buildimage/pull/11594), [1100](https://github.com/sonic-net/sonic-sairedis/pull/1100), [2286](https://github.com/sonic-net/sonic-utilities/pull/2286), [6348](https://github.com/sonic-net/sonic-mgmt/pull/6348), [12026](https://github.com/sonic-net/sonic-buildimage/pull/12026), [1121](https://github.com/sonic-net/sonic-sairedis/pull/1121) & [2365](https://github.com/sonic-net/sonic-utilities/pull/2365)


#### FRR version upgrade from 7.5 to 8.2
Upgrade FRR to version 8.2.2. Build libyang2 required by FRR.

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [10691](https://github.com/sonic-net/sonic-buildimage/pull/10691)


#### hostcfgd Redesign | split hostcfgd into multiple services
This implements the replacement of SubscriberStateTable with ConfigDBConnector. In the past hostcfgd was refactored to use SubscriberStateTable instead of ConfigDBConnector for subscribing to CONFIG_DB updates due to a "blackout" period between hostcfgd pulling the table data down and running the initialization and actually calling listen() on ConfigDBConnector which starts the update handler.

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [10618](https://github.com/sonic-net/sonic-buildimage/pull/10168)


#### Klish CLI for show-tech support
This feature is intended to cover the general approach and method for providing a flexible collection of diagnostic information items. It also considers the basic mechanisms to be used for obtaining the various types of information to be aggregated. It does not address specific details for collection of all supported classes of information.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/SONiC%20Management%20Framework%20Show%20Techsupport%20HLD.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [49](https://github.com/Azure/sonic-mgmt-common/pull/49), [86](https://github.com/Azure/sonic-mgmt-framework/pull/86) & [7816](https://github.com/Azure/sonic-buildimage/pull/7816)


#### Migrated PDDF to Bullseye
This feature updates PDDF utils and common platform APIs for Debian Bullseye

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [9585](https://github.com/sonic-net/sonic-buildimage/pull/9585)


#### Migrated Docker images to Debian "Bullseye"
The docker images to debian bullseye for this release are listed below.

```
        · docker-base-buster
        · docker-config-engine-buster
        · docker-swss-layer-buster
        · docker-database
        · docker-fpm-frr
        · docker-lldp 
        · docker-macsec 
        · docker-mux 
        · docker-orchagent 
        · docker-platform-monitor 
        · docker-router-advertiser 
        · docker-snmp 
        · docker-teamd 
        · docker-sonic-telemetry 
        · docker-pmon-<platform>
        · docker-gbsyncd-credo
        · docker-dhcp-relay 
        · docker-restapi 
        · docker-sonic-p4rt  
        · docker-pde 

```

#### Move Nvidia syncd and pmon to Debian11- "Bullseye"
This impliments the upgrade on nvidia platform for containers such as syncd / saiserver / syncd-rpc and pmon to bullseye 

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [10580](https://github.com/sonic-net/sonic-buildimage/pull/10580)


#### NVGRE/GRE
With the implementation of NVGRE/GRE feature, the following is supported:

- User should be able to create NVGRE tunnel (L2 over L3 tunnel)
- User should be able to create VLAN to VSID mapper entries for the NVGRE tunnel.
- Both VLAN and Bridge to VSID mappers should be supported by the NVGRE tunnel
- Only the decapsulation mappers supported
- YANG model should be created in order to auto-generate CLI by using the SONiC CLI Auto-generation tool.
- CLI for NVGRE tunnel

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/nvgre_tunnel/nvgre_tunnel.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [869](https://github.com/sonic-net/SONiC/pull/869), [1953](https://github.com/sonic-net/sonic-swss/pull/1953), [9136](https://github.com/sonic-net/sonic-buildimage/pull/9136), [549](https://github.com/sonic-net/sonic-swss-common/pull/549), [1915](https://github.com/sonic-net/sonic-utilities/pull/1915)


#### Password Hardening
The password hardening feature implements the requirements, architecture and configuration details of password hardening feature in switches Sonic OS based.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/passw_hardening/hld_password_hardening.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [874](https://github.com/sonic-net/SONiC/pull/874/), [2121](https://github.com/Azure/sonic-utilities/pull/2121), [5503](https://github.com/Azure/sonic-mgmt/pull/5503), [10322](https://github.com/Azure/sonic-buildimage/pull/10322) & [10323](https://github.com/Azure/sonic-buildimage/pull/10323)


#### PINS - Batched programming requests for higher throughput
This implements two new APIs will be introduced into the ProducerStateTable. There will be no change in the existing ProducerStateTable method implementations. There is also no change in the ConsumerStateTable implementation as it can already process batches. The entire change is backward compatible.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/5a5922499b388acafa85dd3c9a64520514e01946/doc/pins/batch_requests_api_hld.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [959](https://github.com/sonic-net/SONiC/pull/959), [588](https://github.com/sonic-net/sonic-swss-common/pull/588), [7](https://github.com/sonic-net/sonic-pins/pull/7) & [10566](https://github.com/sonic-net/sonic-buildimage/pull/10566)


#### Platform support for Edgecore AS4630/AS7326/AS7816/AS5835
This feature impliments the sonic-buildimage changes needed to support in platform for AS4630-pe, AS5835-X, AS7326, AS7816 switch models (currently broken in master).

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [10053](https://github.com/Azure/sonic-buildimage/pull/10053)


#### Queue statistics based on queue configurations and not max
Currently in SONiC all ports queue and pg counters are created by default with the max possible amount of counters. This feature change this behavior to poll only configured counters provided by the config DB BUFFER_PG and BUFFER_QUEUE tables.It also improves performance by filtering unconfigured queue/pg counters on init.

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [2143](https://github.com/sonic-net/sonic-swss/pull/2143), [2315](https://github.com/sonic-net/sonic-swss/pull/2315) & [2199](https://github.com/sonic-net/sonic-utilities/pull/2199)


#### Route Flow counters (based on generic counters)
With the implementation of NVGRE/GRE feature, the following is supported:

- Generic Counters shall be used as Flow Counters introduced by the feature
- Flow Counters for routes shall be configured using prefix patterns. 
- Flow Counters shall be bound the matching routes regardless how these routes are added - manually (static) or via FRR
- Adding route entry shall be automatically bound to counter if counter is enabled and pattern matches
- Removing route entry shall be automatically unbound if the entry is previously bound
- To support default route, pattern "0.0.0.0" and "::" shall be treated as exact match instead of pattern match

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/flow_counters/routes_flow_counters.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [908](https://github.com/sonic-net/SONiC/pull/908), [2094](https://github.com/sonic-net/sonic-swss/pull/2094), [2031](https://github.com/sonic-net/sonic-utilities/pull/2031), [2069](https://github.com/sonic-net/sonic-utilities/pull/2069), [9814](https://github.com/sonic-net/sonic-buildimage/pull/9814) & [5736](https://github.com/sonic-net/sonic-mgmt/pull/5736)


#### SONiC Generic Update and Rollback
The SONiC Generic Update and Rollback feature is to standardize the way to do partial updates, to take checkpoints and finally to rollback the configurations for SONiC.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/config-generic-update-rollback/SONiC_Generic_Config_Update_and_Rollback_Design.md) and below mentioned PR's for more details. 

 **Pull Requests** : [1536](https://github.com/sonic-net/sonic-utilities/pull/1536), [8187](https://github.com/sonic-net/sonic-buildimage/pull/8187), [1599](https://github.com/sonic-net/sonic-utilities/pull/1599), [8632](https://github.com/sonic-net/sonic-buildimage/pull/8632), [1794](https://github.com/sonic-net/sonic-utilities/pull/1794), [1762](https://github.com/sonic-net/sonic-utilities/pull/1762), [1831](https://github.com/sonic-net/sonic-utilities/pull/1831), [1864](https://github.com/sonic-net/sonic-utilities/pull/1864), [1856](https://github.com/sonic-net/sonic-utilities/pull/1856), [1901](https://github.com/sonic-net/sonic-utilities/pull/1901), [1885](https://github.com/sonic-net/sonic-utilities/pull/1885), [4485](https://github.com/sonic-net/sonic-mgmt/pull/4485), [4716](https://github.com/sonic-net/sonic-mgmt/pull/4716), [1923](https://github.com/sonic-net/sonic-utilities/pull/1923), [1934](https://github.com/sonic-net/sonic-utilities/pull/1934), [1919](https://github.com/sonic-net/sonic-utilities/pull/1919), [4736](https://github.com/sonic-net/sonic-mgmt/pull/4736), [4775](https://github.com/sonic-net/sonic-mgmt/pull/4775), [4725](https://github.com/sonic-net/sonic-mgmt/pull/4725), [1929](https://github.com/sonic-net/sonic-utilities/pull/1929), [9295](https://github.com/sonic-net/sonic-buildimage/pull/9295), [9535](https://github.com/sonic-net/sonic-buildimage/pull/9535), [1969](https://github.com/sonic-net/sonic-utilities/pull/1969), [1973](https://github.com/sonic-net/sonic-utilities/pull/1973), [1977](https://github.com/sonic-net/sonic-utilities/pull/1977), [4814](https://github.com/sonic-net/sonic-mgmt/pull/4814), [1981](https://github.com/sonic-net/sonic-utilities/pull/1981), [4839](https://github.com/sonic-net/sonic-mgmt/pull/4839), [4834](https://github.com/sonic-net/sonic-mgmt/pull/4834), [4835](https://github.com/sonic-net/sonic-mgmt/pull/4835), [1988](https://github.com/sonic-net/sonic-utilities/pull/1988), [1983](https://github.com/sonic-net/sonic-utilities/pull/1983), [1987](https://github.com/sonic-net/sonic-utilities/pull/1987), [4875](https://github.com/sonic-net/sonic-mgmt/pull/4875), [9659](https://github.com/sonic-net/sonic-buildimage/pull/9659), [2003](https://github.com/sonic-net/sonic-utilities/pull/2003), [2006](https://github.com/sonic-net/sonic-utilities/pull/2006), [2015](https://github.com/sonic-net/sonic-utilities/pull/2015), [2020](https://github.com/sonic-net/sonic-utilities/pull/2020), [2028](https://github.com/sonic-net/sonic-utilities/pull/2028), [4896](https://github.com/sonic-net/sonic-mgmt/pull/4896), [2008](https://github.com/sonic-net/sonic-utilities/pull/2008), [4915](https://github.com/sonic-net/sonic-mgmt/pull/4915), [4987](https://github.com/sonic-net/sonic-mgmt/pull/4987), [5005](https://github.com/sonic-net/sonic-mgmt/pull/5005), [4580](https://github.com/sonic-net/sonic-mgmt/pull/4580), [5021](https://github.com/sonic-net/sonic-mgmt/pull/5021), [9877](https://github.com/sonic-net/sonic-buildimage/pull/9877), [9880](https://github.com/sonic-net/sonic-buildimage/pull/9880), [5046](https://github.com/sonic-net/sonic-mgmt/pull/5046), [5047](https://github.com/sonic-net/sonic-mgmt/pull/5047), [4811](https://github.com/sonic-net/sonic-mgmt/pull/4811), [5092](https://github.com/sonic-net/sonic-mgmt/pull/5092), [5028](https://github.com/sonic-net/sonic-mgmt/pull/5028), [5002](https://github.com/sonic-net/sonic-mgmt/pull/5002), [1998](https://github.com/sonic-net/sonic-utilities/pull/1998), [2044](https://github.com/sonic-net/sonic-utilities/pull/2044), [5061](https://github.com/sonic-net/sonic-mgmt/pull/5061), [5254](https://github.com/sonic-net/sonic-mgmt/pull/5254), [2092](https://github.com/sonic-net/sonic-utilities/pull/2092), [5234](https://github.com/sonic-net/sonic-mgmt/pull/5234), [5268](https://github.com/sonic-net/sonic-mgmt/pull/5268), [5257](https://github.com/sonic-net/sonic-mgmt/pull/5257), [2104](https://github.com/sonic-net/sonic-utilities/pull/2104), [2103](https://github.com/sonic-net/sonic-utilities/pull/2103), [5116](https://github.com/sonic-net/sonic-mgmt/pull/5116), [10248](https://github.com/sonic-net/sonic-buildimage/pull/10248), [5391](https://github.com/sonic-net/sonic-mgmt/pull/5391), [2120](https://github.com/sonic-net/sonic-utilities/pull/2120), [5398](https://github.com/sonic-net/sonic-mgmt/pull/5398), [5480](https://github.com/sonic-net/sonic-mgmt/pull/5480), [5506](https://github.com/sonic-net/sonic-mgmt/pull/5506), [5509](https://github.com/sonic-net/sonic-mgmt/pull/5509), [1991](https://github.com/sonic-net/sonic-utilities/pull/1991), [10699](https://github.com/sonic-net/sonic-buildimage/pull/10699), [2145](https://github.com/sonic-net/sonic-utilities/pull/2145), [5647](https://github.com/sonic-net/sonic-mgmt/pull/5647), [2174](https://github.com/sonic-net/sonic-utilities/pull/2174), [5692](https://github.com/sonic-net/sonic-mgmt/pull/5692), [2171](https://github.com/sonic-net/sonic-utilities/pull/2171), [5689](https://github.com/sonic-net/sonic-mgmt/pull/5689), [5892](https://github.com/sonic-net/sonic-mgmt/pull/5802), [2212](https://github.com/sonic-net/sonic-utilities/pull/2212), [5645](https://github.com/sonic-net/sonic-mgmt/pull/5645), [5469](https://github.com/sonic-net/sonic-mgmt/pull/5469), [5816](https://github.com/sonic-net/sonic-mgmt/pull/5816), [5847](https://github.com/sonic-net/sonic-mgmt/pull/5847), [5843](https://github.com/sonic-net/sonic-mgmt/pull/5843) & [2234](https://github.com/sonic-net/sonic-utilities/pull/2234)

 **Pull Requests** : These PRs were raised on 202111 release. However the feature was not fully qualified in 202111 release. :[736](https://github.com/Azure/SONiC/pull/736), [1536](https://github.com/Azure/sonic-utilities/pull/1536), [1599](https://github.com/Azure/sonic-utilities/pull/1599),  [1762](https://github.com/Azure/sonic-utilities/pull/1762),  [1794](https://github.com/Azure/sonic-utilities/pull/1794),  [1831](https://github.com/Azure/sonic-utilities/pull/1831),  [1856](https://github.com/Azure/sonic-utilities/pull/1856),  [1864](https://github.com/Azure/sonic-utilities/pull/1864),  [1885](https://github.com/Azure/sonic-utilities/pull/1885),  [1901](https://github.com/Azure/sonic-utilities/pull/1901),  [1919](https://github.com/Azure/sonic-utilities/pull/1919),  [1923](https://github.com/Azure/sonic-utilities/pull/1923),  [1929](https://github.com/Azure/sonic-utilities/pull/1929),  [1934](https://github.com/Azure/sonic-utilities/pull/1934),  [1969](https://github.com/Azure/sonic-utilities/pull/1969),  [1973](https://github.com/Azure/sonic-utilities/pull/1973),  [1977](https://github.com/Azure/sonic-utilities/pull/1977),  [1981](https://github.com/Azure/sonic-utilities/pll/1981),  [1983](https://github.com/Azure/sonic-utilities/pull/1983),  [1987](https://github.com/Azure/sonic-utilities/pull/1987),  [1988](https://github.com/Azure/sonic-utilities/pull/1988),  [2003](https://github.com/Azure/sonic-utilities/pull/2003),  [2006](https://github.com/Azure/sonic-utilities/pull/2006),  [2008](https://github.com/Azure/sonic-utilities/pull/2008),  [2015](https://github.com/Azure/sonic-utilities/pull/2015),  [2020](https://github.com/Azure/sonic-utilities/pull/2020) & [2028](https://github.com/Azure/sonic-utilities/pull/2028) 

 In order to track all the changes related to this feature, refer both the above release PRs.

#### SONIC YANG Support for KDUMP, ACL, MCLAG, BUM Storm Control
This enhances the update on SONiC Yang model to add support for Source MAC, Destination MAC, Ethertype pattern update, VLAN_ID, PCP, DEI fields for SONiC MAC ACL. Also mclag sonic yang and support for Kdump have been added. Changes done on sonic yang for BUM storm control as part of this enhancement. 

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [7917](https://github.com/Azure/sonic-buildimage/pull/7917), [7622](https://github.com/Azure/sonic-buildimage/pull/7622), [7355](https://github.com/Azure/sonic-buildimage/pull/7355) & [10786](https://github.com/Azure/sonic-buildimage/pull/10786) 


#### Sorted next hop ECMP
Under the ToR (Tier0 device) there can be appliances (eg:Firewall/Software-Load Balancer) which maintain state of flows running through them. For better scaling/high-availaibility/fault-tolerance set of appliances are used and connected to differnt ToR's. Not all the flow state that are maintained by these appliances in a set are shared between them. Thus with flow state not being sync if the flow do not end up alawys on to same TOR/Appliance it can cause services (using that flow) degradation and also impact it's availability

To make sure given flow (identidied by 5 tuple) always end up on to same TOR/Appliance we need ECMP ordered support/feature on T1 (Leaf Router). With this feature enable even if flow land's on different T1's (which is common to happen as some link/device in the flow path goes/come to/from maintainence) ECMP memeber being ordered will use same nexthop (T0) and thus same appliace.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/bum_storm_control/bum_storm_control_hld.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [896](https://github.com/sonic-net/SONiC/pull/896), [9651](https://github.com/sonic-net/sonic-buildimage/pull/9651), [2092](https://github.com/sonic-net/sonic-swss/pull/2092) & [989](https://github.com/sonic-net/sonic-sairedis/pull/989)


#### Storm Control (BUM)
This feature supports configuration of Broadcast, Unknown-unicast and unknown-Multicast storm-control independently on physical interfaces. Also, supports threshold rate configuration in kilo bits per second (kbps) in the range of 0 kbps to 100,000,000 kbps (100Gbps).

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/bum_storm_control/bum_storm_control_hld.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [441](https://github.com/sonic-net/SONiC/pull/441), [1306](https://github.com/sonic-net/sonic-swss/pull/1306), [928](https://github.com/sonic-net/sonic-utilities/pull/928), [346](https://github.com/sonic-net/sonic-swss-common/pull/346) & [565](https://github.com/sonic-net/sonic-swss-common/pull/565)


#### Symcrypt integration with OpenSSL
SONiC only uses cryptographic modules validated by FIPS 140-3, Make SONiC compliant with FIPS 140-3. OpenSSL supports engine cryptographic modules in the form of engine objects, and provides a reference-counted mechanism to allow them to be dynamically loaded in and out of the running application. An engine object can implement one or all cryptographic algorithms.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/fips/SONiC-OpenSSL-FIPS-140-3.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [955](https://github.com/sonic-net/SONiC/pull/955), [9573](https://github.com/sonic-net/sonic-buildimage/pull/9573), [10729](https://github.com/sonic-net/sonic-buildimage/pull/10729) &  [2154](https://github.com/sonic-net/sonic-utilities/pull/2154)


#### System Ready Enhancements
This feature implements a new python based System monitor framework is introduced to monitor all the essential system host services including docker wrapper services on an event based model and declare the system is ready. This framework gives provision for docker and host apps to notify its closest up status. CLIs are provided to fetch the current system status and also service running status and its app ready status along with failure reason if any.

Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/system_health_monitoring/system-ready-HLD.md) and below mentioned PR's for more details. 
<br>  **Pull Requests** : [977](https://github.com/sonic-net/SONiC/pull/977), [10479](https://github.com/sonic-net/sonic-buildimage/pull/10479) & [1851](https://github.com/sonic-net/sonic-utilities/pull/1851)


#### Updated PDDF kernel modules in compliance with kernel 5.10 APIs
This enhancement is for modification of code with new kernel 5.10 APIs. And modification of the Makefiles to use 'obj-m' instead of 'subdir-y'

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [9582](https://github.com/sonic-net/sonic-buildimage/pull/9582)

#### Updated PDDF SFP Class with refactored SFP framework
This enchaces all the SFP platform API classes which needed to use SFP refactoring framework. The platforms which use PDDF, derive their SFP API class from a common pddf_sfp.py. Hence pddf_sfp.py needs to comply with SFP refactoring.

Refer below mentioned PR's for more details. 
<br>  **Pull Requests** : [10047](https://github.com/sonic-net/sonic-buildimage/pull/10047)


# Known Issues 
On the 202205 release image, a difference of 0.2 - 0.3 sec is observed (for slower CPU's) when running show cli's. This is reflected in most of the show cli's since many of them import device_info which is still using swsssdk in 202205 release. This is a known observation of this 202205 image.

This known issue, has been fixed in 202211 release through the [PR#10099](https://github.com/sonic-net/sonic-buildimage/pull/10099). As mentioned in the other [PR#16595](https://github.com/sonic-net/sonic-buildimage/issues/16595), the fix is not backported to 202205 branch and hence the issue will continue to exit in 202205 image.

# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.10.2 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.10.2_ReleaseNotes.md)


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Aviz, Broadcom, Cisco, Dell, Edgecore, Google, Intel, Marvell, Microsoft, Nvidia & Target.  

<br> 



