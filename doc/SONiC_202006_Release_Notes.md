# SONiC 201911 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC 202006 release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/Azure/sonic-buildimage/tree/202006 <br>
Image  : https://sonic-jenkins.westus2.cloudapp.azure.com/  (Example - Image for Broadcom based platforms is [here]( https://sonic-jenkins.westus2.cloudapp.azure.com/job/broadcom/job/buildimage-brcm-202006/lastSuccessfulBuild/artifact/target/))

# Dependency Version

|Feature                    | Version  |
| ------------------------- | --------------- |
| Linux kernel version      | linux_4.9.0-11-2 (4.9.189-3+deb9u2)   |
| SAI   version             | SAI v1.5.1    |
| FRR                       | 7.2    |
| LLDPD                     | 0.9.6-1    |
| TeamD                     | 1.28-1    |
| SNMPD                     | 5.7.3+dfsg-1.5    |
| Python                    | 3.6.0-1    |
| syncd                     | 1.0.0    |
| swss                      | 1.0.0    |
| radvd                     | 2.17-2~bpo9+1    |
| isc-dhcp                  | 4.3.5-2 ([PR2946](https://github.com/Azure/sonic-buildimage/pull/2946) )   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |


# Security Updates

1. Kernal upgraded from 4.9.110-3deb9u6 (SONiC Release 201904) to 4.9.168-1+deb9u5 in this SONiC release. 
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-4.9.168-1deb9u5
2. Docker upgraded from 18.09.2\~3-0\~debian-stretch to 18.09.8\~3-0\~debian-stretch. 
   Change log: https://docs.docker.com/engine/release-notes/#18098 

# Feature List

#### BFD SW 100ms interval from FRR 
This document provides functional design and specifications of BFD protocol as defined in RFC 5880, 5881, 5882 and 5883.BFD protocol defines a method of rapid detection of the failure of a forwarding path by checking that the next hop router is alive. The protocol will be able to detect the forwarding path failure in milliseconds depending on the actual configuration. 
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/bfd/BFD_Enhancement_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [3838](https://github.com/Azure/sonic-buildimage/pull/3838) ,[5197](https://github.com/FRRouting/frr/pull/5197)  

#### Build Improvements 
This document provides functional design and specifications of BFD protocol as defined in RFC 5880, 5881, 5882 and 5883.BFD protocol defines a method of rapid detection of the failure of a forwarding path by checking that the next hop router is alive. The protocol will be able to detect the forwarding path failure in milliseconds depending on the actual configuration. 
<br> Refer [HLD document]() and below mentioned PR's for more details. 
<br> **Pull Requests** : [3292](https://github.com/Azure/sonic-buildimage/pull/3292), [4117](https://github.com/Azure/sonic-buildimage/pull/4117), [4425](https://github.com/Azure/sonic-buildimage/pull/4425) 

#### Bulk API for route
This document provides functional design and specifications of BFD protocol as defined in RFC 5880, 5881, 5882 and 5883.BFD protocol defines a method of rapid detection of the failure of a forwarding path by checking that the next hop router is alive. The protocol will be able to detect the forwarding path failure in milliseconds depending on the actual configuration. 
<br> Refer [HLD document]() and below mentioned PR's for more details. 
<br> **Pull Requests** : [1238](https://github.com/Azure/sonic-swss/pull/1238)  

#### CoPP Config/Management 
During SWSS start, the prebuilt copp.json file is loaded as part of start script swssconfig.sh and written to APP DB. CoppOrch then translates it to Host trap/policer tables and programmed to SAI. With the new proposal, the CoPP tables shall be loaded to Config DB instead of APP DB. The default CoPP json file shall be prebuilt to the image and loaded during initialization. Any Config DB entries present shall be configured overwriting the default CoPP tables. This also ensures backward compatibility.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/fdc7cff16b7f42f1a1b01dd506279e3e9f9269cb/doc/copp/CoPP%20Config%20and%20Management.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [358](https://github.com/Azure/sonic-swss-common/pull/358), [1333](https://github.com/Azure/sonic-swss/pull/1333), [4861](https://github.com/Azure/sonic-buildimage/pull/4861)

#### D-Bus to Host Communications 
This document describes a means (framework) for an application executed inside a container to securely request the execution of an operation ("action") by the host OS.This framework is intended to be used by the SONiC management and telemetry containers, but can be extended for other application containers as well.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/mgmt/Docker%20to%20Host%20communication.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4840](https://github.com/Azure/sonic-buildimage/pull/4840)

#### Debian 10 upgrade, base image,driver 

<br> Refer [HLD document]() and below mentioned PR's for more details. 
<br> **Pull Requests** : [145](https://github.com/Azure/sonic-linux-kernel/pull/145), [4711](https://github.com/Azure/sonic-buildimage/pull/4711) 

#### Dynamic port break
Ports can be broken out to different speeds with various lanes in most HW today. However, on SONiC, the port breakout modes are hard-coded in the profiles and only loaded at initial time. In case we need to have a new port breakout mode, we would potentially need a new image or at least need to restart services which would impact the traffic of the box on irrelevant ports. The feature is to address the above issues.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/dynamic-port-breakout/sonic-dynamic-port-breakout-HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4235](https://github.com/Azure/sonic-buildimage/pull/4235), [3910](https://github.com/Azure/sonic-buildimage/pull/3910), [1242](https://github.com/Azure/sonic-swss/pull/1242), [1219](https://github.com/Azure/sonic-swss/pull/1219), [1151](https://github.com/Azure/sonic-swss/pull/1151), [1150](https://github.com/Azure/sonic-swss/pull/1150), [1148](https://github.com/Azure/sonic-swss/pull/1148), [1112](https://github.com/Azure/sonic-swss/pull/1112), [1085](https://github.com/Azure/sonic-swss/pull/1085), [766](https://github.com/Azure/sonic-utilities/pull/766), [72](https://github.com/Azure/sonic-platform-common/pull/72), [859](https://github.com/Azure/sonic-utilities/pull/859), [767](https://github.com/Azure/sonic-utilities/pull/767), [765](https://github.com/Azure/sonic-utilities/pull/765), [3912](https://github.com/Azure/sonic-buildimage/pull/3912), [3911](https://github.com/Azure/sonic-buildimage/pull/3911), [3909](https://github.com/Azure/sonic-buildimage/pull/3909), [3907](https://github.com/Azure/sonic-buildimage/pull/3907), [3891](https://github.com/Azure/sonic-buildimage/pull/3891), [3874](https://github.com/Azure/sonic-buildimage/pull/3874), [3861](https://github.com/Azure/sonic-buildimage/pull/3861), [3730](https://github.com/Azure/sonic-buildimage/pull/3730)

#### Egress shaping (port, queue) 
Quality of Service (QoS) scheduling and shaping features enable better service to certain traffic flows.Queue scheduling provides preferential treatment of traffic classes mapped to specific egress queues. SONiC supports SP, WRR, and DWRR scheduling disciplines.Queue shaping provides control of minimum and maximum bandwidth requirements per egress queue for more effective bandwidth utilization. Egress queues that exceed an average transmission rate beyond the shaper max bandwidth will stop being serviced. Additional ingress traffic will continue to be stored on the egress queue until the queue size is exceeded which results in tail drop.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/41e55d2762e9267454a4910b42a1eb7ad07acda8/doc/qos/scheduler/SONiC_QoS_Scheduler_Shaper.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1296](https://github.com/Azure/sonic-swss/pull/1296), [991](https://github.com/Azure/sonic-swss/pull/991)

#### FW utils extension: SSD upgrade 
A modern network switch is a sophisticated equipment which consists of many auxiliary components which are responsible for managing different subsystems (e.g., PSU/FAN/QSFP/EEPROM/THERMAL) and providing necessary interfaces (e.g., I2C/SPI/JTAG).Basically these components are complex programmable logic devices with it's own HW architecture and software. It is very important to always have the latest recommended software version to improve device stability, security and performance. In order to make software update as simple as possible and to provide a nice user frindly interface for various maintenance operations (e.g., install a new FW or query current version) we might need a dedicated FW utility.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/fwutil/fwutil.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4764](https://github.com/Azure/sonic-buildimage/pull/4764), [4758](https://github.com/Azure/sonic-buildimage/pull/4758), [941](https://github.com/Azure/sonic-utilities/pull/941), [942](https://github.com/Azure/sonic-utilities/pull/942), [87](https://github.com/Azure/sonic-platform-common/pull/87), [82](https://github.com/Azure/sonic-platform-common/pull/82)

#### Gearbox
The Ethernet switches of today have evolved and are entering several key segments providing switch chips for enterprise, data-center, and carrier, as well as optical transceivers, Gearbox PHYs and 25Gbps Re-timers. If the platform/hardware supports it, the PHY may be configurable to speeds including 10G, 25G, 40G, 50G, and 100G, and beyond. Some platforms contain an external PHY, while others have PHYs embedded in the switch ASIC (Internal PHY). The abstraction interface contains a set of SAI APIs providing new functionality in support of the most recent PHY advancements and requirements. Through utilizing this new external PHY interface, this project adds configuration and management capabilities for these new external PHY requirements.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/gearbox/gearbox_mgr_design.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [347](https://github.com/Azure/sonic-swss-common/pull/347), [931](https://github.com/Azure/sonic-utilities/pull/931), [1321](https://github.com/Azure/sonic-swss/pull/1321), [624](https://github.com/Azure/sonic-sairedis/pull/624), [4851](https://github.com/Azure/sonic-buildimage/pull/4851) 

#### Getting docker ready for Debian 10

<br> Refer [HLD document]() and below mentioned PR's for more details. 
<br> **Pull Requests** : [4671](https://github.com/Azure/sonic-buildimage/pull/4671), [4727](https://github.com/Azure/sonic-buildimage/pull/4727), [4726](https://github.com/Azure/sonic-buildimage/pull/4726), [4665](https://github.com/Azure/sonic-buildimage/pull/4665), [4515](https://github.com/Azure/sonic-buildimage/pull/4515),  [4598](https://github.com/Azure/sonic-buildimage/pull/4598), [4529](https://github.com/Azure/sonic-buildimage/pull/4529), [4480](https://github.com/Azure/sonic-buildimage/pull/4480)

#### Management Framework (Phase 2)
Management framework makes use of the translation library (Translib) written in golang to convert the data models exposed to the management clients into the Redis ABNF schema format. Supported management servers can make use of the Translib to convert the incoming payload to SONiC ABNF schema and vice versa depending on the incoming request. Translib will cater to the needs of REST and gNMI servers. Later the Translib can be enhanced to support other management servers if needed. This framework will support both standard and custom YANG models for communication with the corresponding management servers. 
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/34cac1aabdc865fc41cbe064a2ab2442645524b1/doc/mgmt/Management%20Framework.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [18](https://github.com/Azure/sonic-mgmt-framework/pull/18), [19](https://github.com/Azure/sonic-mgmt-framework/pull/19), [25](https://github.com/Azure/sonic-mgmt-framework/pull/25)

#### PDDF advance to SONiC Platform 2.0, BMC 
SONiC OS is portable across different network devices with supported ASIC via Switch Abstraction Interface (SAI). These devices primarily differ in the way various device specific hardware components are accessed, and thus require custom device drivers and python plugins. Each platform vendor implements these custom device drivers and plugins. The feature requirement is to support a SONiC platform driver development framework to enable rapid development of custom device drivers and plugins.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/platform/brcm_pdk_pddf.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4756](https://github.com/Azure/sonic-buildimage/pull/4756), [940](https://github.com/Azure/sonic-utilities/pull/940), [92](https://github.com/Azure/sonic-platform-common/pull/92)

#### PDK - Platform Development Environment
This feature describes the high level design details on how the SONiC PDE is constructed as well as details on the PDE test suite. The PDE is available to ODMs and others looking to add new platform support, and it optimizes the development and qualification process. It offers a pre-canned, minimal code package to which the ODM can add their necessary platform driver files and static configuration files. Furthermore, the PDE will provide a test suite where platform developers can quickly test their drivers and configuration files to resolve issues more easily without relying on the full SONiC application and infrastructure to be in place.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/platform/pde.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [3778](https://github.com/Azure/sonic-buildimage/pull/3778), [28](https://github.com/Azure/sonic-platform-pdk-pde/pull/28)

#### PDK - Platform Driver Development Framework
SONiC OS is portable across different network devices with supported ASIC via Switch Abstraction Interface (SAI). These devices primarily differ in the way various device specific hardware components are accessed, and thus require custom device drivers and python plugins. Each platform vendor implements these custom device drivers and plugins. The feature requirement is to support a SONiC platform driver development framework to enable rapid development of custom device drivers and plugins.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/master/doc/platform/brcm_pdk_pddf.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [3387](https://github.com/Azure/sonic-buildimage/pull/3387), [624](https://github.com/Azure/sonic-utilities/pull/624), [62](https://github.com/Azure/sonic-platform-common/pull/62)

#### Port Mirroring
This feature describes the high level design details on Port/Port-channel mirroring support, dynamic session management, ACL rules can continue to use port/ERSPAN sessions as the action, Configuration CLI for mirror session.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/e8c86d1b3a03d6320727ff148966081869461e4a/doc/SONiC_Port_Mirroring_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1314](https://github.com/Azure/sonic-swss/pull/1314), [936](https://github.com/Azure/sonic-utilities/pull/936) 

#### Port Mirroring
This feature describes the high level design details on Port/Port-channel mirroring support, dynamic session management, ACL rules can continue to use port/ERSPAN sessions as the action, Configuration CLI for mirror session.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/e8c86d1b3a03d6320727ff148966081869461e4a/doc/SONiC_Port_Mirroring_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [1314](https://github.com/Azure/sonic-swss/pull/1314), [936](https://github.com/Azure/sonic-utilities/pull/936) 

#### Proxy ARP  
When an interface is enabled with "proxy_arp", the same is enabled in the kernel. ASIC ARP packet action is also updated to trap these packets to CPU in those interfaces.
<br> Refer [HLD Document](https://github.com/Azure/SONiC/blob/master/doc/arp/Proxy%20Arp.md) for more details. 
<br> **Pull Requests** :  [617](https://github.com/Azure/SONiC/pull/617)

#### Pytest 100% moved from ansible to Pytest 

#### SPytest

<br> Refer [HLD Document]() for more details. 
<br> **Pull Requests** :  [1533](https://github.com/Azure/sonic-mgmt/pull/1533)

#### System health and system LED
System health monitor is intended to monitor both critical services and peripheral device status and leverage system log, system status LED to and CLI command output to indicate the system status.In current SONiC implementation, we already have Monit which is monitoring the critical services status and also have a set of daemons.System health monitoring service will not monitor the critical services or devices directly, it will reuse the result of Monit and PMON daemons to summary the current status and decide the color of the system health LED.
<br> Refer [HLD document](https://github.com/Azure/SONiC/blob/fd9abf13f8aa2a2c2ca241bc9e3a7dde369cae3f/doc/system_health_monitoring/system-health-HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [4835](https://github.com/Azure/sonic-buildimage/pull/4835), [4829](https://github.com/Azure/sonic-buildimage/pull/4829)

#### Thermal control 
Thermal control daemon has been added to monitor the temperature of devices (CPU, ASIC, optical modules, etc) and the running status of fan. It retrieves the switch device temperatures via platform APIs and raises alarms when the high/low thresholds are hit.It also stores temperature values fetched from sensors and thermal device running status to the DB.
<br> Refer  [HLD Document](https://github.com/Azure/SONiC/blob/master/thermal-control-design.md) for more details.
<br> **Pull Requests** :  [73](https://github.com/Azure/sonic-platform-common/pull/73), [777](https://github.com/Azure/sonic-utilities/pull/777), [49](https://github.com/Azure/sonic-platform-daemons/pull/49), [3949](https://github.com/Azure/sonic-buildimage/pull/3949),[832](https://github.com/Azure/sonic-utilities/pull/832) 


<br>


# SAI APIs

Please find the list of API's classified along the newly added SAI features. For further details on SAI API please refer [SAI_1.5_Release_notes]([https://github.com/kannankvs/md2/blob/master/SAI_1.5%20Release%20notes.md](https://github.com/kannankvs/md2/blob/master/SAI_1.5 Release notes.md))

| S.No | Feature                     | API                                                          |
| ---- | --------------------------- | ------------------------------------------------------------ |
| 1    | TAM                         | 1. sai_create_tam_report_fn<br/>   2. sai_remove_tam_int_f<br/>   3. sai_set_tam_int_attribute_fn<br/>   4. sai_get_tam_int_attribute_fn<br/>   5. sai_tam_telemetry_get_data_fn |
| 2    | NAT                         | 1. sai_create_nat_range_fn<br/>   2. sai_remove_nat_range_fn<br/>   3. sai_get_nat_range_attribute_fn<br/>   4. sai_get_nat_range_attribute_fn<br/>   5. sai_create_nat_fn<br/>   6. sai_remove_nat_fn<br/>   7. sai_set_nat_attribute_fn<br/>   8. sai_get_nat_attribute_fn |
| 3    | sFLOW                       | 1. sai_hostif_type_genetlink<br/>   2. sai_hostif_attr_genetlink_mcgrp_name<br/>   3. sai_hostif_table_entr_channel_type_genetlink |
| 4    | Generic Resource Monitoring | 1. sai_object_type_get_availability                          |
| 5    | SAI counter                 | 1. sai_create_counter_fn<br/>   2. sai_remove_counter_fn<br/>   3. sai_set_counter_attribute_fn<br/>   4. sai_get_counter_attribute_fn<br/>   5. sai_get_counter_stats_fn<br/>   6. sai_get_counter_stats_ext_fn<br/>   7. sai_clear_counter_stats_fn |
| 6    | Drop Counters               | 1. sai_create_debug_counter_fn<br/>   2. sai_remove_debug_counter_fn<br/>   3. sai_set_debug_counter_attribute_fn<br/>   4. sai_get_debug_counter_attribute_fn |



# Contributors 

SONiC community would like to thank all the contributors from various companies and the individuals who has contributed for the release. Special thanks to the major contributors - Microsoft, Broadcom, DellEMC, Mellanox, Alibaba, Linkedin, Nephos & Aviz. 

<br>



