## Authors
Alibaba : Weitang Zheng  
Molex: Jimmy Jin

## Table of Contents
- [Authors](#authors)
- [Table of Contents](#table-of-contents)
- [List of Changes](#list-of-changes)
  - [Definitions and abbreviations](#definitions-and-abbreviations)
  - [1. SONiC for optical network introduction](#1-sonic-for-optical-network-introduction)
  - [2. optical transport network device introduction](#2-optical-transport-network-device-introduction)
  - [3. SONiC for OTN architecture](#3-sonic-for-otn-architecture)
  - [4. How to implement OTN features in SONiC](#4-how-to-implement-otn-features-in-sonic)
    - [4.1 How to add OTN platforms and devices](#41-how-to-add-otn-platforms-and-devices)
    - [4.2 How to customize feature and service](#42-how-to-customize-feature-and-service)
    - [4.3 Add OTAI, Synd-OT and OTSS services](#43-add-otai-synd-ot-and-otss-services)
      - [4.3.1 Monolithic SWSS and Syncd](#431-monolithic-swss-and-syncd)
      - [4.3.2 Microservice OTN services](#432-microservice-otn-services)
      - [4.3.3 Monolithic vs Microservice OTN services](#433-monolithic-vs-microservice-otn-services)
      - [4.3.4 The OTN services introduction](#434-the-otn-services-introduction)
    - [4.4 Add OTN required enhancement](#44-add-otn-required-enhancement)
      - [4.4.1 In mgmt-common module, three new enhancements are added.](#441-in-mgmt-common-module-three-new-enhancements-are-added)
      - [4.4.2 Add auto-generated OTN CLI](#442-add-auto-generated-otn-cli)
      - [4.4.3 Support peripheral devices PM monitoring and alarms](#443-support-peripheral-devices-pm-monitoring-and-alarms)
  - [5. Key OTN requirements for SONiC](#5-key-otn-requirements-for-sonic)
    - [5.1 RESTCONF](#51-restconf)
    - [5.2 gNMI](#52-gnmi)
    - [5.3 CLI](#53-cli)
    - [5.4 Performance Management (PM)](#54-performance-management-pm)
    - [5.5 Alarm Management](#55-alarm-management)

## List of Changes
| Version | Changes | Name | Date |
| :-----| :---- | :----- | :----- |
| V0.1 | Initial Draft | Weitang Zheng | 2024-6-18 |
| V0.2 | Update the CLI auto generation section | Jimmy Jin | 2024-7-30 |

### Definitions and abbreviations 

Definitions/Abbreviation|Description
------------------------|-----------
OTSS| Optical Transport State Service
OTAI| Optcial Transport Abstraction Interface
OTN| Optical Transport Network
CRUD| CREATE, READ, UPDATE and DELETE
OA| Optical Amplifier
OSC| Optical Supervisory Channel
OLP| Optical Line Protection
VOA|Optical Attenuator
OTDR| Optical Time Domain Reflectometer

### 1. SONiC for optical network introduction
In recent years, the optical transport network (OTN) for data center interconnection (DCI) has been emerged to provide high-speed, low-latency, and reliable interconnections between data centers. The OTN network has transformed to openness and disaggregation, due to the advent of digital coherent technology, the practices of software-defined networking (SDN), and the large demand of DCI networks. Modular OTN equipment with standardized northbound interfaces and data models are widely deployed in the DCI industry.

However the network operating systems (NOSes) running on these open and disaggregated optical network device are remain proprietary NOS and vary among different OTN equipment vendors. These proprietary NOSes offer diverse performances and alarms functionalities, CLI capabilities, and security features with different release schedules, which increase the Capital expenditures (CapEx) and operating expenses (OpEx) in a large scale DCI network. 

To overcome this, SONiC for OTN project is proposed to expand SONiC to support the optical transport network. Then SONiC can be deployed to the end to end packet and optical network. It can support optical transponders and muxponders, optical line systems such as optical line protection (OLP), optical amplifiers (OA), wavelength selective switches (WSS), which can provide optical interconnections between IP switch and routers.

<img src="../../images/otn/sonic-otn-transponder-open-line-system.png" alt="transponder and open line system with sonic-otn" style="zoom: 35%;" />

<img src="../../images/otn/sonic-otn-packet-optical-system.png" alt="packet optical and open line system with sonic-otn" style="zoom: 35%;" />

### 2. optical transport network device introduction
The optical transport network device provides high-speed, reliable and efficient data transmission over optical fibers. For DCI, the optical transport network device is typically 1RU (Rack Unit) and 2RU chassis with multiple optical linecard, FAN, PSU and control units. All these optical linecard are pluggable and provide different functionalities.

<img src="../../images/otn/otn-device-overview.png" alt="otn device overview" style="zoom: 35%;" />

Although these optical linecard provide different functionalities and diverse between different OTN device vendors, these optical linecard are composed by the same basic optical component units. These optical components offers the common optical transmission functionalities such as:
* Transponders and Transceivers: Convert electrical signals from servers and network equipment into optical signals for transmission over fiber optics
* Multiplexer (Mux): combine multiple optical signals of different wavelengths onto a single optical fiber for transmission.
* Demultiplexer (Demux): separate multiple optical signals of different wavelengths from a single optical fiber.
* Optical Line Protection (OLP): automatically switching traffic from a primary optical path to a backup path when a fault is detected.
* Optical Amplifier (OA): amplify the optical signal to a higher power level to increase the transmission distance over optical fiber.
* Wavelength Selective Switch (WSS): dynamically route specific wavelengths of light to different directions.
* Optical Supervisory Channel (OSC): channel used for transmitting management, control information alongside the payload channels.
* Variable Optical Attenuator (VOA): attenuate optical signal power level.
* Optical Channel Monitor (OCM): OCM is used to monitor and analyze the optical spectrum of optical signals.
* Optical Time-Domain Reflectometer (OTDR): OTDR is used to measure the attenuation and reflection loss along the fiber.

<img src="../../images/otn/optical-linecard-and-components.png" alt="optical linecard and component" style="zoom: 35%;" />

The control unit (CU) is the main control plane component of the optical transport network device. The OTN device's NOS runs on the CU, and interacts with optical linecar's autonomous systems which are MUC software or embedded operating system. A typical optical NOS architecture on CU has four layers:
* Northbound applications layer: provides Restconf, Netconf, gNMI, CLI and SNMP interfaces
* System applications layer: provides message handler, optical control, management network, in-service software upgrade, and configuration managers, etc.
* Hardware Abstraction layer (HAL): provides hardware abstraction layer for optical linecard, FAN, PSU, EEPROM, etc.
* Linux kernel layer: provides Linux kernel and network stack
  
<img src="../../images/otn/OTN-NOS-architecture.png" alt="otn operating system architecture" style="zoom: 35%;" />

### 3. SONiC for OTN architecture
In order to expand SONiC to support OTN, multiple OTN services and enhancements are introduced to fulfill OTN product requirements. The OTN system maximally reuses the existing SONiC architecture and features, and minimizes the impact on the existing SONiC architecture and features. 

For an OTN device, user can compile the SONiC binary with the following command, and run the binary on the target OTN device.
```
make configure PLATFORM=[OTN_PLATFORMS] PLATFORM_ARCH=arm64
OTN_PLATFORMS = [ot-accelink, ot-molex, ot-infinera, ot-vs]
make target/sonic-OTN_PLATFORMS.bin
```

The prefix `ot-` stands for the optical transport platform, which is used to distinguish whether the target platform is optical transport or not. The SONiC system can initialize the target services and module features based on the platform type.
The following new features for optical transport device are proposed:
1. Enhance the mgmt-framework to support OTN features  
   Supports multiple Optical OpenConfig YANG models and enables querying and setting data across a Multi-ASIC architecture from/to multiple optical linecards

2. Enhance the gNMI module to support subscribing to an URL without specifying a key.

3. Enhance the PMON module to support performance monitoring (PM) and alarm monitoring for peripheral devices.

4. Introduce OTN cli commands in sonic-utilities，and auto generated CLI commands based on Openconfig Yang models.

5. Introduce Optical Transport State Service (OTSS), Syncd for optical transport (Syncd-OT), and optical transport abstraction interface (OTAI).

6. Introduce optical transport platforms and device in sonic-buildimage repository, enable OTSS, Syncd-OT and OTAI on optical transport platform.

The following diagram shows the SONiC for OTN architecture. The platform type is used as the feature toggle of the SONiC system. When the platform type start with "ot-", the SONiC system will enable all OTN features and disable unnecessary IP layer features.

<img src="../../images/otn/sonic-otn-architecture.png" alt="sonic otn architecture" style="zoom: 35%;" />

There are three modifications to the SONiC system.
1. Add OTN platforms and devices in sonic-buildimage repository.
2. Customize features and services based on the OTN platform type
   * Disable IP layer and unnecessary features, including dhcp-relay container, snmp container, teamd container, etc.
   * Disable SWSS container and Syncd container.
   * Keep the LLDP container and BGP container, but enable only one global instance without per-asic-scope instances.
   * Add and enable OTSS and Syncd-OT instances per-asic-scope.
3. Add OTN required enhancements in sonic-platform-common module and sonic-utilities module.

Here is an example of running docker images on the `virtual-ot` platform with 4 ASICs (optical linecard). It contains 4 instances of Syncd-OT and OTSS, 5 instances of redis database, 1 global instance of pmon, lldp, mgmt-framework, gNMI, bgp and eventd.
```
admin@sonic:~$ docker ps
CONTAINER ID   IMAGE                                COMMAND                  CREATED         STATUS              PORTS     NAMES
dfeeb018a154   docker-syncd-ot-vs:latest            "/usr/local/bin/supe…"   4 minutes ago   Up 4 minutes                  syncd-ot2
82de24801ef4   docker-syncd-ot-vs:latest            "/usr/local/bin/supe…"   4 minutes ago   Up 4 minutes                  syncd-ot3
0670ff941482   docker-orchagent-ot:latest           "/usr/bin/docker-ini…"   6 minutes ago   Up 6 minutes                  otss2
c77ac1b8964c   docker-orchagent-ot:latest           "/usr/bin/docker-ini…"   6 minutes ago   Up 6 minutes                  otss3
b71da3b963e9   docker-orchagent-ot:latest           "/usr/bin/docker-ini…"   5 weeks ago     Up 6 minutes                  otss1
0e210df99993   docker-syncd-ot-vs:latest            "/usr/local/bin/supe…"   5 weeks ago     Up 4 minutes                  syncd-ot1
3f1db908acf3   docker-orchagent-ot:latest           "/usr/bin/docker-ini…"   5 weeks ago     Up 6 minutes                  otss0
fa1a131a2681   docker-syncd-ot-vs:latest            "/usr/local/bin/supe…"   5 weeks ago     Up 4 minutes                  syncd-ot0
9a9790c8f9cf   docker-platform-monitor:latest       "/usr/bin/docker_ini…"   5 weeks ago     Up About a minute             pmon
6e4f1ac3bb0b   docker-sonic-mgmt-framework:latest   "/usr/local/bin/supe…"   5 weeks ago     Up About a minute             mgmt-framework
3e1a822c8156   docker-lldp:latest                   "/usr/bin/docker-lld…"   5 weeks ago     Up About a minute             lldp
2b4014c5bcad   docker-sonic-gnmi:latest             "/usr/local/bin/supe…"   5 weeks ago     Up About a minute             gnmi
445c9515ae9e   docker-fpm-frr:latest                "/usr/bin/docker_ini…"   5 weeks ago     Up 4 minutes                  bgp
99df879bc10f   docker-eventd:latest                 "/usr/local/bin/supe…"   5 weeks ago     Up 6 minutes                  eventd
4d8e139ed7cd   docker-database:latest               "/usr/local/bin/dock…"   5 weeks ago     Up 6 minutes                  database0
27f7ea8cf95d   docker-database:latest               "/usr/local/bin/dock…"   5 weeks ago     Up 6 minutes                  database3
47b2f2a37d0c   docker-database:latest               "/usr/local/bin/dock…"   5 weeks ago     Up 6 minutes                  database1
f11c2a50d535   docker-database:latest               "/usr/local/bin/dock…"   5 weeks ago     Up 6 minutes                  database2
db6a10516000   docker-database:latest               "/usr/local/bin/dock…"   5 weeks ago     Up 6 minutes                  database
admin@sonic:~$
```

### 4. How to implement OTN features in SONiC
#### 4.1 How to add OTN platforms and devices
Add multiple new otn platforms types in `sonic-buildimage/platform` folder, the optical platforms include the prefix 'ot-' in the platform name. The optical platform folder contains an optical platform specific target files for Syncd-OT, ONIE, OTAI library, etc.

```
sonic-buildimage/platform
├── ot-accelink
├── ot-cisco
├── ot-infinera
├── ot-molex
├── ot-vs
│   ├── docker-syncd-ot-vs
│   │   ├── Dockerfile.j2
│   │   ├── critical_processes
│   │   └── supervisord.conf
│   ├── docker-syncd-ot-vs.dep
│   ├── docker-syncd-ot-vs.mk
│   ├── kvm-image.dep
│   ├── kvm-image.mk
│   ├── one-image.dep
│   ├── one-image.mk
│   ├── onie.dep
│   ├── onie.mk
│   ├── platform.conf
│   ├── rules.dep
│   ├── rules.mk
│   ├── sonic-version.dep
│   ├── sonic-version.mk
│   ├── syncd-ot-vs.dep
│   └── syncd-ot-vs.mk
```
Then add multiple OTN device in the device folder. This folder contains an OTN device specific configuration files for ASIC, PMON, SKU, default linecard configuration templates and flexcounter configurations, etc. For an OTN platform, the platform_asic should start with "ot-" prefix, the ASIC number stands for the number of optical linecards in the system.
```
sonic-buildimage/device/
├── virtual-ot
│   └── x86_64-ot_kvm_x86_64_4_asic-r0
│       ├── asic.conf
│       ├── default_sku
│       ├── installer.conf
│       ├── linecards
│       │   ├── e110c
│       │   │   ├── config_db.json.j2
│       │   │   └── flexcounter.json
│       │   └── p230c
│       │       ├── L1_400G_CA_100GE
│       │       ├── config_db.json.j2
│       │       └── flexcounter.json
│       ├── platform_asic
│       ├── plugins
│       │   └── eeprom.py
│       └── pmon_daemon_control.json
```

#### 4.2 How to customize feature and service
SONiC provides two mechanisms to customize feature and services. 
* In "rules/config", multiple IP layer features can be disabled on the OTN platform.
* In the "files/build_templates/init_cfg.json.j2", if the platform type start with "ot-", 
  1) the WSS, Syncd, dhcp_relay, and snmp services are disabled.
  2) the OTSS and Syncd-OT services are enabled per-asic-scope.
  3) the LLDP and BPG services are enabled with only one global instance, without per-asic-scope instances.
```
{%- if sonic_asic_platform.startswith('ot-') %}
    {% do features.append(("otss", "enabled", false, "enabled")) %}
    {% do features.append(("syncd-ot", "enabled", false, "enabled")) %}
    {% do features.append(("swss", "disabled", false, "enabled")) %}
    {% do features.append(("syncd", "disabled", false, "enabled")) %}
    {% do features.append(("snmp", "disabled", true, "enabled")) %}
    {% do features.append(("bgp", "enabled", false, "enabled")) %}
    {% do features.append(("dhcp_relay", "disabled", false, "enabled")) %}
{%- endif %}
```

#### 4.3 Add OTAI, Synd-OT and OTSS services
There were two options to manage OTN components in the SONiC platform.
1) Monolithic SWSS and Syncd. Embed OTN features in the SWSS, Syncd and OTN definitions in SAI.
2) Microservice OTN services. Introduce pure OTN services OTSS, Syncd-OT, and OTN abstraction interface (OTAI)  

The SONiC-OTN workgroup prefers the OTN microservice architecture.

##### 4.3.1 Monolithic SWSS and Syncd
In this option, the OTN features are implemented and embedded in the SWSS and Syncd container. New OTN components and objects' APIs, structures and parameters are defined in the SAI.

<img src="../../images/otn/otn-monolithic-swss-syncd.png" alt="sonic otn monolithic swss and syncd" style="zoom: 35%;" />

The platform prefix `ot-` is the feature toggle to enable and disable the OTN features in SWSS and Syncd container. Different OTN specific features are embedded in the SWSS, Syncd and SAI source code. For example,
* In SWSS, different OTN component manager deamons, syncd deamons, and orchagent processes are enabled for OTN platforms.
* In SWSS, special initialization flow for OTN platforms are introduced, for example, the optical linecard pre-configuration, optical linecard hotplug handling.
* In SWSS, support OTN specific operations, for example, optical linecard warm and cold reboot, OLP switch to primary and secondary path, etc.
* In SWSS and Syncd, configure the flexcounter to support different optical linecard specific metrics.
* In SWSS and Syncd, enable and disable different features and deamons based on the IP platform or OTN platform, for one example, the fast-reboot feature is disabled for OTN platforms.
* In Syncd, historical performance metrics, alarms are enabled for OTN platforms.
* In SAI, new OTN components, notfication callbacks, structures, attributes, annotations are defined.
* In SAI, Syncd and SWSS, mulitple OTN notifications are defined and handled, for example, the optical components' alarms, OTDR and OCM data reporting notification, optical linecard status update notification, etc.

##### 4.3.2 Microservice OTN services
In this option, the OTN features are implemented by two new services, the Optical Transport State Service (OTSS) and Syncd for optical transport (Syncd-OT). Optical Transport Abstraction Interface (OTAI) is introduced to manage the OTN components and objects with standard interfaces.

<img src="../../images/otn/otn-microservice-otss-syncd-ot.png" alt="sonic otn microservice otss and syncd-ot" style="zoom: 35%;" />

The OTSS and Syncd-OT services are in parrallel with the SWSS and Syncd services. On IP platforms, the OTSS and Syncd-OT services are disabled. On OTN platform, the SWSS and Syncd services are disabled. All OTN specific features are implemented and isolated in the OTSS and Syncd-OT containers.

The OTSS shares the common utilities in the `sonic-swss-common` repository. The Syncd-OT shares some common infrastrues with the Syncd container, for example the `meta`, `redis-remote`, `flexcounter` and `notification`. The OTAI shares some common infrastrue with the SAI, for example the `metadatatypes`, `serializer`, `deserializer` and `parser.pl`. The OTN workgroup can mannually merge common infrastrues from the syncd and SAI repositories to syncd-OT and OTAI, but a common infrastrue library repostory `sonic-syncd-common` is recommended as softwre evolution in the future. 

##### 4.3.3 Monolithic vs Microservice OTN services
There are pros and cons to both monolithic and microservice architectures for OTN services, but the SONiC-OTN workgroup prefers the microservice architecture. Here’s a summary of benefits of microservice OTN architecture.
* Reduce risks  
OTSS and Syncd-OT microservices limits the impact on the IP applications, all OTN modifications are isolated in docker containers and loose coupling with the IP applications. Any failure of the OTN services will not impact the IP applications. User can re-deploy impacting IP or OTN microservices to improve SONiC system recoverability.

* Innovate faster  
With OTSS and Syncd-OT microservices, both IP and OTN microservices can be innovated on certain components more quickly and independantly. It much easier to design, develop and test these IP and OTN microservices than the monolithic SWSS and Syncd.  

* Reduce total cost of ownership  
With microservice architecutre, it's more cost-effective in the long term, user can scale microservice applications horizontally by device compute resource and hareware type. 

* Team capability  
Developers focus on a specific microservice, they don't need to understand how other microservices work. Developers only need IP or OTN domain knowledge to develop the microservice.

##### 4.3.4 The OTN services introduction
[Optical Transport Abstraction Interface (OTAI)](./OTAI-v0.0.1-specification.md) is a standard interface for managing and controlling the optical transport components.
OTAI provides CRUD APIs for all OTN components and objects, notifications for OTN status change and data reporting. All attributes defined in OTAI are compatible with the OpenConfig model.

[Syncd-OT](./otn_syncd_hld.md) provides a mechanism to allow the synchronization of the optical transport network state with actual optical transport components and hardware. It includes the initialization, the configuration, the PM collections and the alarms of the optical components.

[The Optical Transport State Service (OTSS)](./otn_otss_hld.md) is a collection of software that provides a database interface for communication with and state representation of optical network applications and optical transport component hardware.

The OTSS and Syncd-OT services are enabled on the OTN platform, and support Multi-ASIC architecture. On OTN platform, one optical linecard is an ASIC, so one OTSS instance, one Syncd-OT instance and one database instance are assigned to manage one optical linecard.

<img src="../../images/otn/otn-services-multi-asic.png" alt="sonic otn architecture" style="zoom: 35%;" />


#### 4.4 Add OTN required enhancement
##### 4.4.1 In mgmt-common module, three new enhancements are added. 
1. Supports multi-ASIC architecture. Here is the [pull request](https://github.com/sonic-net/SONiC/pull/1701) for this enhancement. The mgmt-common module interacts with multiple database instances in Multi-ASIC architecture. The applications in mgmt-common dispatch RESTCONF requests to the correct database instance based on the request URL.
For instance, the following URL accesses the optical amplifier instance `AMPLIFIER-1-1-1`'s `enable` status, the `AMPLIFIER-1-1-1` stands for the optical amplifier in chassis `1`, slot `1` and component id `1`. All optical components with slot `1` are mapped to ASIC ID `1`.
```
/restconf/data/openconfig-optical-amplifier:optical-amplifier/amplifiers/amplifier=AMPLIFIER-1-1-1/config/enabled
``` 

2. Supports following OpenConfig optical YANG modules. 
   * openconfig-optical-amplifier.yang
   * openconfig-terminal-device.yang
   * openconfig-channel-monitor.yang
   * openconfig-transport-line-protection.yang
   * openconfig-optical-attenuator.yang
   * openconfig-wavelength-router.yang
   * openconfig-telemetry.yang
   * openconfig-interfaces.yang
   * openconfig-lldp.yang
   * openconfig-system.yang
   * openconfig-platform.yang

3. Support query all instance data without a key specified in mgmt-framework and mgmt-common. In gNMI docker, user can subscribe to a path without a key specified. For example,the gNMI module subscribe all existing logical channels in all optical transponders with the single path `/openconfig-terminal-device:terminal-device/logical-channels/channel/otn/state`. Here are the other paths examples.
```
/openconfig-terminal-device:terminal-device/logical-channels/channel/otn/state
/openconfig-system:system/alarms/alarm/state
/openconfig-platform:components/component/openconfig-terminal-device:optical-channel/state
/openconfig-platform:components/component/state
......
```

##### 4.4.2 Add auto-generated OTN CLI
SONiC-OTN project adopts openconfig yang model, https://github.com/openconfig/public/tree/master/release/models/optical-transport, for optical network device support. Therefore, these yang models and corresponding SONiC extension annotations are added into sonic-mgmt-common for supporting OTN REST APIs.

An automatic CLI generation mechanism is introduced as part of OTN project to eliminate the manual effort of writing click based CLI. 

The mechanism is a SONiC compatible Docker image, based on [SONiC application extension mechanism](https://github.com/sonic-net/SONiC/tree/master/doc/sonic-application-extension). It can be built stand alone, then installed on a SONiC system at run time, as well as built into a sonic image at build time using [sonic-buildimage](https://github.com/sonic-net/sonic-buildimage).

Please see [HLD](https://github.com/sonic-otn/SONiC-OTN/blob/main/documentation/openconfig-cli-autogen-HLD.md) and [prototype](https://github.com/jjin62/sonic-openconfig-cli) for details.

##### 4.4.3 Support peripheral devices PM monitoring and alarms
OTN product requires the performance data monitoring and alarm monitoring for peripheral devices. A new PM module is introduced to implement this feature. Here is the high level design for this enhancement in `sonic-platform-common` [ont_pmon_hld](https://github.com/sonic-otn/SONiC-OTN/blob/main/documentation/otn_pmon_hld.md)


### 5. Key OTN requirements for SONiC
#### 5.1 RESTCONF
* Support multi-ASIC architecture and manage multiple optical linecard.
* Support Synchronized create and set RESTCONF request.
* Support openconfig-platform model with components such as chassis, main control units, fans, power supplies, linecard, OSC, OCM, OTDR, optical transceivers, OLP, WSS, OA, panel ports, VOA, etc.  
* Support openconfig-system model with hostname, timezone, and NTP, along with alarm reporting and system reset RPC functions.  
* Support openconfig-terminal-device model with logical-channels, OTN, ethernet, LLDP, assignments and operational-modes.  
* Support openconfig-interfaces model with interface and ethernet nodes.  
* Support openconfig-lldp model for OSC and transponder client-side ethernet .  
* Support openconfig-telemetry model with sensor-groups, destination-groups.
* Support openconfig-optical-amplifier model with amplifier, supervisory-channels.  
* Support openconfig-channel-monitor model with channel-monitors, channels.  
* Support openconfig-transport-line-protection model with aps-module, ports.
* Support openconfig-optical-attenuator model with attenuators.  
* Support openconfig-wavelength-router model with media-channels. 

#### 5.2 gNMI
* Support OTN Openconfig Yang models in gNMI dial-out and dial-in mode.
* Support subscribing an URL path without a key specified.
* Support configuring multiple Telemetry data collection servers.  
* Support alarm notifications when the Telemetry collector is unreachable.  

#### 5.3 CLI
* Support quering running configuration, current and historical performance and alarm; 
* Support clearing historical alarms and resetting current performance statistics.  
* Support in-service software upgrades for chassis and optical linecard.
* Support warm and cold reset functions for chassis and optical linecard.  
* Support backup and restore configurations, reset configurations to factory default.  
* Support quering all telemetry sensor-group, destination-group, and subscription.  
* Support configuration the IP address of dual management and OSC interfaces.  
* Support OSPF protocol over OSC interfaces and dual mamagement interfaces.  
* Support showing version for chassis, main control units, linecards and OTAI interfaces.   
* Support configure and query all optical components (transceivers, OA, VOA, OSC, OLP, panel ports, OCMs, OTDRs, and WSS on optical linecards) status and parameters defined in OTAI.  
* Support quering LLDP neighbor information over OSC interface.  
 
#### 5.4 Performance Management (PM)
* Support current and historical performance statistics with 15-minute and 24-hour periods.  
* Retain historical PM data for 7 days.
* PM data must contain a VALID field to indicate data's validity within the period.  
* Device's analog performance statistics must include maximum value, time of maximum value occurrence, minimum value, time of minimum value occurrence, and average value.  
* Device must not lose historical performance data after cold and warm resets.  

#### 5.5 Alarm Management
* The device must support alarm reporting with Openconfig alarm definitions 
* The optical alarm types must be defined in OTAI alarm types;   
* Device must support historical alarm queries and clearance, 
* Retain historical alarm data for 7 days; 
* Device must not lose historical alarm data after cold and warm resets. 
* Device must support alarm suppression, where higher business impact alarms will suppress lower business impact alarms.


