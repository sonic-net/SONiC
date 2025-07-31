# SONiC 201911 Release Notes

This document captures the new features added and enhancements done on existing features/sub-features for the SONiC 201911 release.



# Table of Contents

 * [Branch and Image Location](#branch-and-image-location)
 * [Dependency Version](#dependency-version)
 * [Security Updates](#security-updates)
 * [Feature List](#feature-list)
 * [SAI APIs](#sai-apis)
 * [Contributors](#contributors)


# Branch and Image Location  

Branch : https://github.com/sonic-net/sonic-buildimage/tree/201911 <br>
Image  : https://sonic-jenkins.westus2.cloudapp.azure.com/  (Example - Image for Broadcom based platforms is [here]( https://sonic-jenkins.westus2.cloudapp.azure.com/job/broadcom/job/buildimage-brcm-201911/lastSuccessfulBuild/artifact/target/))

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
| isc-dhcp                  | 4.3.5-2 ([PR2946](https://github.com/sonic-net/sonic-buildimage/pull/2946) )   |
| sonic-telemetry           | 0.1    |
| redis-server/ redis-tools | 5.0.3-3~bpo9+2    |
| Debian version			| Stretch (Debian version 9)	|


# Security Updates

1. Kernal upgraded from 4.9.110-3deb9u6 (SONiC Release 201904) to 4.9.168-1+deb9u5 in this SONiC release. 
   Change log: https://tracker.debian.org/media/packages/l/linux/changelog-4.9.168-1deb9u5
2. Docker upgraded from 18.09.2\~3-0\~debian-stretch to 18.09.8\~3-0\~debian-stretch. 
   Change log: https://docs.docker.com/engine/release-notes/#18098 

# Feature List

#### Build time improvements 
This document describes few options to improve SONiC build time. To split the work we will consider that SONiC has two stages: 1. debian/python packages compilation <- relatively fast 2. docker images build <- slower espessially when several users are building in parallel.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/sonic-build-system/build_system_improvements.md) and below mentioned PR's for more details. 
<br> **Pull Requests** : [911](https://github.com/sonic-net/sonic-swss/pull/911) ,[280](https://github.com/sonic-net/sonic-swss-common/pull/280)  ,  [461](https://github.com/sonic-net/sonic-sairedis/pull/461)  , [3048](https://github.com/sonic-net/sonic-buildimage/pull/3048)  ,  [3049](https://github.com/sonic-net/sonic-buildimage/pull/3049) 

#### Configurable  drop counters 
This feature is to provides better packet drop visibility in SONiC by providing a mechanism to count and classify packet drops that occur due to different reasons.This is done by adding support for SAI debug counters to SONiC. Supported counters are PORT_INGRESS_DROPS , PORT_EGRESS_DROPS, SWITCH_INGRESS_DROP & SWITCH_EGRESS_DROPS. A CLI tool will be provided for users to manage and configure their own drop counters.
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/drop_counters/drop_counters_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Requests** :  [308](https://github.com/sonic-net/sonic-swss-common/pull/308) ,  [520](https://github.com/sonic-net/sonic-sairedis/pull/520) ,   [1075](https://github.com/sonic-net/sonic-swss/pull/1075)  ,   [1093](https://github.com/sonic-net/sonic-swss/pull/1093)  ,   [688](https://github.com/sonic-net/sonic-utilities/pull/688) 
                                                  
#### Egress mirroring support and ACL action capability check 
Added support for egress mirror action. To query ACL action list supported by ASIC per stage and put this information in STATE DB SWITCH_CAPABILITY table and to perform secondary query for ACL action attributes which parameters are enum values (e.g. for PACKET_ACTION - DROP,FORWARD). 
<br> Refer [HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/acl/acl_stage_capability.md) and below mentioned PR's for more details. 
<br> **Pull Requests** :  [963](https://github.com/sonic-net/sonic-swss/pull/963)   , [1019](https://github.com/sonic-net/sonic-swss/pull/1019)  ,  [575](https://github.com/sonic-net/sonic-utilities/pull/575) ,  [481](https://github.com/sonic-net/sonic-sairedis/pull/481) 

#### HW resource monitor 
This document describes the high level design of verification the hardware resources consumed by a device. The hardware resources which are currently verified are CPU, RAM and HDD. This implementation will be integrated in test cases written on Pytest framework. 
<br> Refer[HLD document](https://github.com/sonic-net/SONiC/blob/master/doc/DUT_monitor_HLD.md) and below mentioned PR for more details. 
<br> **Pull Request** :  [1121](https://github.com/sonic-net/sonic-mgmt/pull/1121)        

#### L3 performance and scaling enhancements 
When sending a lot of ARP/ND requests in a burst, ARP entries are getting purged from the kernel while the later set of ARP entries was still getting added. The sequence of add/remove is in such a way that we were never able to cross ~2400 entries. Currently the max rate for ARP/ND is 600 packets, we will be increasing it to higher number(8000) in CoPP file to improve the learning time.
<br> Refer [HLD Document](https://github.com/sonic-net/SONiC/blob/89abd4938d792215b75d801e87b47ccf2c22f111/doc/L3_performance_and_scaling_enchancements_HLD.md) and below mentioned PR's for more details. 
<br> **Pull Request** :  [1048](https://github.com/sonic-net/sonic-swss/pull/1048)        

####  Log analyzer to pytest 
In the root conftest there is implemented "loganalyzer" pytest fixture, which starts automatically for all test cases.If loganalyzer find specified messages which corresponds to defined regular expressions, it will display found messages and pytest will generate 'error'.
Refer [Loganalyzer API usage example](https://github.com/yvolynets-mlnx/sonic-mgmt/blob/78a71ebccdc44bd62e81ff4b12dd84cb2c0ea34d/tests/loganalyzer/README.md) for more details. 
<br> **Pull Request** :  [1048](https://github.com/sonic-net/sonic-mgmt/pull/1048) 
       
#### Management Framework 
Management framework is a SONiC application which is responsible for providing various common North Bound Interfaces (NBIs) for the purposes of managing configuration and status on SONiC switches. The application manages coordination of NBI’s to provide a coherent way to validate, apply and show configuration. Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md) 
<br> **Pull Requests** :  [18](https://github.com/sonic-net/sonic-mgmt-framework/pull/18)   , [23](https://github.com/sonic-net/sonic-gnmi/pull/23)  ,   [3488](https://github.com/sonic-net/sonic-buildimage/pull/3488)  , [659](https://github.com/sonic-net/sonic-utilities/pull/659) 

#### Management VRF
Management VRF (mvrf) feature provides a separation between the management network traffic and the data plane network traffic using the linux CGROUPS based on l3mdev. Management interface (eth0) shall be enslaved in l3mdev. Management applications like SSH shall use the enslaved eth0 and corresponding mvrf routing table for management traffic.
<br> Refer below PR's for more details. 
<br> **Pull Requests** :  [2585](https://github.com/sonic-net/sonic-buildimage/pull/2585)  , [2608](https://github.com/sonic-net/sonic-buildimage/pull/2608)  ,  [3204](https://github.com/sonic-net/sonic-buildimage/pull/3204)  ,  [463](https://github.com/sonic-net/sonic-utilities/pull/463)  ,  [472](https://github.com/sonic-net/sonic-utilities/pull/472)  ,  [627](https://github.com/sonic-net/sonic-utilities/pull/627)  ,  [3586](https://github.com/sonic-net/sonic-buildimage/pull/3586) 



#### Multi-DB optimization 
Creating multiple database instances help us to separate the databases based on their operation frequency or their role in the whole SONiC system, for example, like state database and loglevel database are not key features, we can avoid them affecting read and write APPL_DB or ASIC_DB via multiple database instances. 
<br> Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/ed69d427dcf358299b2c1b812e59a1e26a4ef4a5/doc/database/multi_database_instances.md) for more details.
<br> **Pull Request** :  [52](https://github.com/sonic-net/sonic-py-swsssdk/pull/52)      

#### NAT 
Network Address Translation (NAT) router enables private IP networks to communicate to the public networks (internet) by translating the private IP address to globally unique IP address. It also provides security by hiding the identity of the host in private network. This feature supports Source NAT, Destination NAT ,Static NAT/NAPT, Dynamic NAT/NAPT, NAT zones, Twice NAT/NAPT nd support of VRF. 
<br> For more details refer [HLD Document](https://github.com/kirankella/SONiC/blob/nat_doc_changes/doc/nat/nat_design_spec.md).
<br> **Pull Requests** :  [3494](https://github.com/sonic-net/sonic-buildimage/pull/3494) , [1059](https://github.com/sonic-net/sonic-swss/pull/1059)  ,  [645](https://github.com/sonic-net/sonic-utilities/pull/645)  ,  [100 ](https://github.com/sonic-net/sonic-linux-kernel/pull/100) ,  [304](https://github.com/sonic-net/sonic-swss-common/pull/304)  ,  [519](https://github.com/sonic-net/sonic-sairedis/pull/519) 

#### Platform test  
This test plan is to check the functionalities of platform related software components. These software components are for managing platform hardware, including FANs, thermal sensors, SFP, transceivers, pmon, etc.The software components for managing platform hardware on Mellanox platform is the hw-management package. 
<br> Refer [Platform testplan](https://github.com/sonic-net/SONiC/blob/master/doc/pmon/sonic_platform_test_plan.md) for more details. 
<br> **Pull Requests** :  [915](https://github.com/sonic-net/sonic-mgmt/pull/915)   , [980](https://github.com/sonic-net/sonic-mgmt/pull/980)  , [1079](https://github.com/sonic-net/sonic-mgmt/pull/1079) 

#### Proxy ARP  
When an interface is enabled with "proxy_arp", the same is enabled in the kernel. ASIC ARP packet action is also updated to trap these packets to CPU in those interfaces.
<br> Refer [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/arp/Proxy%20Arp.md) for more details. 
<br> **Pull Requests** :  [617](https://github.com/sonic-net/SONiC/pull/617) 

####  sFlow 
The CLI is enhanced to provide configuring and display of sFlow parameters including sflow collectors, agent IP, sampling rate for interfaces. The CLI configurations currently only interact with the CONFIG_DB. The newly introduced sflow container consists of an instantiation of the InMon's hsflowd daemon.
<br> Refer   [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/sflow/sflow_hld.md) for more details.
<br> **Pull Requests** :  [94](https://github.com/sonic-net/sonic-linux-kernel/pull/94)  , [299](https://github.com/sonic-net/sonic-swss-common/pull/299)  , [498](https://github.com/sonic-net/sonic-sairedis/pull/498)  ,  [1012](https://github.com/sonic-net/sonic-swss/pull/1012)  ,  [1011](https://github.com/sonic-net/sonic-swss/pull/1011)  ,  [3251](https://github.com/sonic-net/sonic-buildimage/pull/3251)  ,  [592 ](https://github.com/sonic-net/sonic-utilities/pull/592) 

#### SSD diagnostic tolling 
Add to SONiC an ability to check storage health state. Basic functionality will be implemented as a CLI command. Optionally pmon daemon could be added for constant disk state monitoring. 
<br> Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/ssdhealth_design.md) for more details.
<br> **Pull Requests** :  [587](https://github.com/sonic-net/sonic-utilities/pull/587)  , [47](https://github.com/sonic-net/sonic-buildimage/pull/47) ,  [3218](https://github.com/sonic-net/sonic-buildimage/pull/3218) 

#### Sub-port support 
A sub port interface is a logical interface that can be created on a physical port or a port channel.A sub port interface serves as an interface to either a .1D bridge or a VRF, but not both. This design focuses on the use case of creating a sub port interface on a physical port or a port channel and using it as a router interface to a VRF. 
<br> Refer  [HLD Document](https://github.com/wendani/SONiC/blob/a3e669e6778c272fc571a8bf3bd78e7eb75a8ec7/doc/sonic-sub-port-intf-hld.md) for more details. 
<br> **Pull Requests** :   [998](https://github.com/opencomputeproject/SAI/pull/998) , [284](https://github.com/sonic-net/sonic-swss-common/pull/284) , [969](https://github.com/sonic-net/sonic-swss/pull/969)  , [871](https://github.com/sonic-net/sonic-swss/pull/871) , [3412](https://github.com/sonic-net/sonic-buildimage/pull/3412) , [3422](https://github.com/sonic-net/sonic-buildimage/pull/3422) , [3413](https://github.com/sonic-net/sonic-buildimage/pull/3413) , [638](https://github.com/sonic-net/sonic-utilities/pull/638) , [642](https://github.com/sonic-net/sonic-utilities/pull/642) , [651](https://github.com/sonic-net/sonic-utilities/pull/651) |

#### Thermal control 
Thermal control daemon has been added to monitor the temperature of devices (CPU, ASIC, optical modules, etc) and the running status of fan. It retrieves the switch device temperatures via platform APIs and raises alarms when the high/low thresholds are hit.It also stores temperature values fetched from sensors and thermal device running status to the DB.
<br> Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/master/thermal-control-design.md) for more details.
<br> **Pull Requests** :  [73](https://github.com/sonic-net/sonic-platform-common/pull/73), [777](https://github.com/sonic-net/sonic-utilities/pull/777), [49](https://github.com/sonic-net/sonic-platform-daemons/pull/49), [3949](https://github.com/sonic-net/sonic-buildimage/pull/3949),[832](https://github.com/sonic-net/sonic-utilities/pull/832) 

#### VRF 
Sonic supports multiple loopback interfaces. Each loopback interfaces can belong to different VRF instances. In this feature we also support BGP and VRF support for FRR config template. 
<br> Refer  [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/vrf/sonic-vrf-hld.md) for more details.
<br> **Pull Requests** :  [3952](https://github.com/sonic-net/sonic-buildimage/pull/3952) , [943](https://github.com/sonic-net/sonic-swss/pull/943) , [1065](https://github.com/sonic-net/sonic-mgmt/pull/1065) 

#### ZTP 
Zero Touch Provisioning (ZTP) service can be used by users to configure a fleet of switches using common configuration templates. Switches booting from factory default state should be able to communicate with remote provisioning server and download relevant configuration files and scripts to kick start more complex configuration steps. ZTP service takes user input in JSON format. Some of the supported features are - Dynamically generate DHCP client configuration based on current ZTP state and Added support to request and process hostname when using DHCPv6. 
<br> Refer [HLD Document](https://github.com/sonic-net/SONiC/blob/master/doc/ztp/ztp.md) for more details.
<br> **Pull Requests** :  [3227](https://github.com/sonic-net/sonic-buildimage/pull/3227) , [3298](https://github.com/sonic-net/sonic-buildimage/pull/3298)  , [1000](https://github.com/sonic-net/sonic-swss/pull/1000) , [3299](https://github.com/sonic-net/sonic-buildimage/pull/3299) , [12](https://github.com/sonic-net/sonic-ztp/pull/12), [599](https://github.com/sonic-net/sonic-utilities/pull/599) ,[715](https://github.com/sonic-net/sonic-utilities/pull/715)


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



