# SONiC 202006 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC 202006 release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/sonic-net/sonic-buildimage/tree/202006 <br>
Image  : https://sonic-jenkins.westus2.cloudapp.azure.com/  (Example - Image for Broadcom based platforms is [here]( https://sonic-jenkins.westus2.cloudapp.azure.com/job/broadcom/job/buildimage-brcm-202006/lastSuccessfulBuild/artifact/target/))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_4.9.0-11-2 (4.9.189-3+deb9u2)   |
| SAI   version             | SAI v1.6.3    |
| FRR                       | 7.2    |
| LLDPD                     | 0.9.6-1    |
| TeamD                     | 1.28-1    |
| SNMPD                     | 5.7.3+dfsg-1.5    |
| Python                    | 3.6.0-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.17-2~bpo9+1    |
| isc-dhcp                  | 4.3.5-2 ([PR2946](https://github.com/sonic-net/sonic-buildimage/pull/2946) )   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Continues to use Stretch (Debian version 9)	|

Note : The kernel version is migrated to the version that is mentioned in the first row in the above 'Dependency Version' table.


# Security Updates

1. Kernel upgraded from 4.9.110-3deb9u6 (SONiC Release 201904) to 4.9.168-1+deb9u5 in this SONiC release. 
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-4.9.168-1deb9u5
2. Docker upgraded from 18.09.2\~3-0\~debian-stretch to 18.09.8\~3-0\~debian-stretch. 
   Change log: https://docs.docker.com/engine/release-notes/#18098 

# Feature List

#### Build Improvements 
DPKG caching framework provides the infrastructure to cache the sonic module/target .deb files into a local cache by tracking the target dependency files.SONIC build infrastructure is designed as a plugin framework where any new source code can be easily integrated into sonic as a module and that generates output as a .deb file.This provides a huge improvement in build time and also supports the true incremental build by tracking the dependency files.
<br> **Pull Requests** : [3292](https://github.com/sonic-net/sonic-buildimage/pull/3292), [4117](https://github.com/sonic-net/sonic-buildimage/pull/4117), [4425](https://github.com/sonic-net/sonic-buildimage/pull/4425) 

#### Bulk API for route
This feature provides bulk routes and next hop group members as coded in the PR mentioned below.
<br> **Pull Requests** : [1238](https://github.com/sonic-net/sonic-swss/pull/1238)  

#### D-Bus to Host Communications 
This document describes a means (framework) for an application executed inside a container to securely request the execution of an operation ("action") by the host OS.This framework is intended to be used by the SONiC management and telemetry containers, but can be extended for other application containers as well.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4840](https://github.com/sonic-net/sonic-buildimage/pull/4840)

#### Debian 10 upgrade, base image,driver 
This feature provides change in kernel version. By changing the kernel ABI from version 6 to version 6-2, this will allow to disable the kernel ABI check which Debian performs at the very end of the kernel build.
<br> **Pull Requests** : [145](https://github.com/sonic-net/sonic-linux-kernel/pull/145), [4711](https://github.com/sonic-net/sonic-buildimage/pull/4711) 

#### Dynamic port breakout
Ports can be broken out to different speeds with various lanes in most HW today. However, on SONiC, before this release, the port breakout modes are hard-coded in the profiles and only loaded at initial time. In case we need to have a new port breakout mode, we would potentially need a new image or at least need to restart services which would impact the traffic of the box on irrelevant ports. The feature is to address the above issues.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4235](https://github.com/sonic-net/sonic-buildimage/pull/4235), [3910](https://github.com/sonic-net/sonic-buildimage/pull/3910), [1242](https://github.com/sonic-net/sonic-swss/pull/1242), [1219](https://github.com/sonic-net/sonic-swss/pull/1219), [1151](https://github.com/sonic-net/sonic-swss/pull/1151), [1150](https://github.com/sonic-net/sonic-swss/pull/1150), [1148](https://github.com/sonic-net/sonic-swss/pull/1148), [1112](https://github.com/sonic-net/sonic-swss/pull/1112), [1085](https://github.com/sonic-net/sonic-swss/pull/1085), [766](https://github.com/sonic-net/sonic-utilities/pull/766), [72](https://github.com/sonic-net/sonic-platform-common/pull/72), [859](https://github.com/sonic-net/sonic-utilities/pull/859), [767](https://github.com/sonic-net/sonic-utilities/pull/767), [765](https://github.com/sonic-net/sonic-utilities/pull/765), [3912](https://github.com/sonic-net/sonic-buildimage/pull/3912), [3911](https://github.com/sonic-net/sonic-buildimage/pull/3911), [3909](https://github.com/sonic-net/sonic-buildimage/pull/3909), [3907](https://github.com/sonic-net/sonic-buildimage/pull/3907), [3891](https://github.com/sonic-net/sonic-buildimage/pull/3891), [3874](https://github.com/sonic-net/sonic-buildimage/pull/3874), [3861](https://github.com/sonic-net/sonic-buildimage/pull/3861), [3730](https://github.com/sonic-net/sonic-buildimage/pull/3730)

#### Egress shaping (port, queue) 
Quality of Service (QoS) scheduling and shaping features enable better service to certain traffic flows.Queue scheduling provides preferential treatment of traffic classes mapped to specific egress queues. SONiC supports SP, WRR, and DWRR scheduling disciplines.Queue shaping provides control of minimum and maximum bandwidth requirements per egress queue for more effective bandwidth utilization. Egress queues that exceed an average transmission rate beyond the shaper max bandwidth will stop being serviced. Additional ingress traffic will continue to be stored on the egress queue until the queue size is exceeded which results in tail drop.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/41e55d2762e9267454a4910b42a1eb7ad07acda8/doc/qos/scheduler/SONiC_QoS_Scheduler_Shaper.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1296](https://github.com/sonic-net/sonic-swss/pull/1296), [991](https://github.com/sonic-net/sonic-swss/pull/991)

#### FW utils extension  
A modern network switch is a sophisticated equipment which consists of many auxiliary components which are responsible for managing different subsystems (e.g., PSU/FAN/QSFP/EEPROM/THERMAL) and providing necessary interfaces (e.g., I2C/SPI/JTAG).Basically these components are complex programmable logic devices with it's own HW architecture and software. It is very important to always have the latest recommended software version to improve device stability, security and performance. In order to make software update as simple as possible and to provide a nice user frindly interface for various maintenance operations (e.g., install a new FW or query current version) we might need a dedicated FW utility.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/fwutil/fwutil.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4764](https://github.com/sonic-net/sonic-buildimage/pull/4764), [4758](https://github.com/sonic-net/sonic-buildimage/pull/4758), [941](https://github.com/sonic-net/sonic-utilities/pull/941), [942](https://github.com/sonic-net/sonic-utilities/pull/942), [87](https://github.com/sonic-net/sonic-platform-common/pull/87), [82](https://github.com/sonic-net/sonic-platform-common/pull/82)

#### Getting docker ready for Debian 10
This change adds support to build dockers using buster as base.sonic-mgmt-framework docker is updated to build using buster as base.
<br> **Pull Requests** : [4671](https://github.com/sonic-net/sonic-buildimage/pull/4671), [4727](https://github.com/sonic-net/sonic-buildimage/pull/4727), [4726](https://github.com/sonic-net/sonic-buildimage/pull/4726), [4665](https://github.com/sonic-net/sonic-buildimage/pull/4665), [4515](https://github.com/sonic-net/sonic-buildimage/pull/4515),  [4598](https://github.com/sonic-net/sonic-buildimage/pull/4598), [4529](https://github.com/sonic-net/sonic-buildimage/pull/4529), [4480](https://github.com/sonic-net/sonic-buildimage/pull/4480)

#### Port Mirroring
This feature describes the high level design details on Port/Port-channel mirroring support, dynamic session management, ACL rules can continue to use port/ERSPAN sessions as the action, Configuration CLI for mirror session.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/e8c86d1b3a03d6320727ff148966081869461e4a/doc/SONiC_Port_Mirroring_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1314](https://github.com/sonic-net/sonic-swss/pull/1314), [936](https://github.com/sonic-net/sonic-utilities/pull/936) 

#### Proxy ARP  
When an interface is enabled with "proxy_arp", the same is enabled in the kernel. ASIC ARP packet action is also updated to trap these packets to CPU in those interfaces.
<br> Refer [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/arp/Proxy%20Arp.md) for more details. 
<br> **Pull Requests** :  [617](https://github.com/sonic-net/SONiC/pull/617)

#### Pytest 100% moved from ansible to Pytest 

#### SPytest
This is an initial version of spytest framework and first set of test scripts for 202006 release.
<br> Refer [HLD Document](https://github.com/sonic-net/sonic-mgmt/blob/master/spytest/Doc/intro.md) for more details.
<br> **Pull Requests** :  [1533](https://github.com/sonic-net/sonic-mgmt/pull/1533)

#### Thermal control 
Thermal control daemon has been added to monitor the temperature of devices (CPU, ASIC, optical modules, etc) and the running status of fan. It retrieves the switch device temperatures via platform APIs and raises alarms when the high/low thresholds are hit.It also stores temperature values fetched from sensors and thermal device running status to the DB.In addition it provides the policy based thermal control and fan speed tuning in configuration, and we are able to customize and/or add the platform specific policies as needed. 
<br> Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/master/thermal-control-design.md) for more details.
<br> **Pull Requests** :  [73](https://github.com/sonic-net/sonic-platform-common/pull/73), [777](https://github.com/sonic-net/sonic-utilities/pull/777), [49](https://github.com/sonic-net/sonic-platform-daemons/pull/49), [3949](https://github.com/sonic-net/sonic-buildimage/pull/3949),[832](https://github.com/sonic-net/sonic-utilities/pull/832)

#### PSU and FAN LED management 

The PSU and FAN LED on switch will be set according to PSU and FAN presence and running status, for example if there is a failure happening to PSU or FAN, the corresponding LED will be set to red. 
<br>Refer [HLD Document](https://github.com/sonic-net/SONiC/blob/master/thermal-control-design.md) and [HLD Document](https://github.com/sonic-net/SONiC/pull/591) for more details.
<br> **Pull Requests** : [4437](https://github.com/sonic-net/sonic-buildimage/pull/4437);[1580](https://github.com/sonic-net/sonic-mgmt/pull/1580);[881](https://github.com/sonic-net/sonic-utilities/pull/881);[54](https://github.com/sonic-net/sonic-platform-daemons/pull/54);[83](https://github.com/sonic-net/sonic-platform-common/pull/83)

#### PSU, thermal and FAN plugin extension

On new plugins for fan, thermal and PSU the PSU plugin was extended with voltage, current and power supported, and the fan and thermal plugins were introduced.
<br> **Pull Requests** : [4041](https://github.com/sonic-net/sonic-buildimage/pull/4041)




<br>


# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.6.3 Release Notes](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI_1.6.3_ReleaseNotes.md)

| S.No | Feature                     | 
| ---- | --------------------------- |
| 1    | MACSEC                      |
| 2    | System Port API             |


# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Microsoft, Broadcom, DellEMC, Mellanox, Alibaba, Linkedin, Nephos & Aviz. 

<br>



