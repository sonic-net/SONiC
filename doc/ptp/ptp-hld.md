# PTP Feature

### High Level Design document

### Table of Contents

- [PTP Feature](#ptp-feature)
    - [High Level Design document](#high-level-design-document)
    - [Table of Contents](#table-of-contents)
    - [Revision](#revision)
    - [About this manual](#about-this-manual)
    - [Scope](#scope)
    - [Abbreviations](#abbreviations)
- [1 Introduction](#1-introduction)
- [2 Feature Design](#2-feature-design)
  - [2.1 Operational Flow](#21-operational-flow)
  - [2.2 PTP Container](#22-ptp-container)
  - [2.3 Configuration Templates](#23-configuration-templates)
  - [2.4 Time Distribution Network Variants](#24-time-distribution-network-variants)
    - [2.4.1 Ordinary Clock](#241-ordinary-clock)
    - [2.4.2 Boundary Clock](#242-boundary-clock)
    - [2.4.3 Transparent Clock](#243-transparent-clock)
    - [2.4.4 IPv4/IPv6 Unicast transports](#244-ipv4ipv6-unicast-transports)
    - [2.4.5 IPv4/IPv6 Multicast transports](#245-ipv4ipv6-multicast-transports)
    - [2.4.6 L2 transport](#246-l2-transport)
  - [2.5 Hardware Features Support](#25-hardware-features-support)
    - [2.5.1 Hardware Timestamping Configuration](#251-hardware-timestamping-configuration)
    - [2.5.2 Static Delay Asymmetry Configuration](#252-static-delay-asymmetry-configuration)
    - [2.5.3 SyncE](#253-synce)
    - [2.5.4 G.8275.1 Support](#254-g82751-support)
  - [2.6 Chassis/Multi-ASIC support](#26-chassismulti-asic-support)
- [3 Requirements Roadmap](#3-requirements-roadmap)
  - [3.1 Phase 1](#31-phase-1)
  - [3.2 Phase 2](#32-phase-2)
- [4 Configuration](#4-configuration)
- [5 Module Design](#5-module-design)
  - [5.1 PTP Container](#51-ptp-container)
  - [5.2 orchagent](#52-orchagent)
  - [5.3 Syncd Updates](#53-syncd-updates)
  - [5.4 SAI Interface](#54-sai-interface)
  - [5.5 SAI implementations and ASIC Device Driver Updates](#55-sai-implementations-and-asic-device-driver-updates)
  - [5.6 Linux Ethernet Device Update](#56-linux-ethernet-device-update)
  - [5.7 PHC Device](#57-phc-device)
- [6 Data Model](#6-data-model)
  - [6.1 SONiC DBs](#61-sonic-dbs)
    - [6.1.1 Config\_DB](#611-config_db)
      - [6.1.1.1 Feature Config](#6111-feature-config)
      - [6.1.1.2 Port Config](#6112-port-config)
      - [6.1.1.3 PTP Config](#6113-ptp-config)
    - [6.1.2 APPL\_DB](#612-appl_db)
      - [6.1.2.1 Switch ptp port mode](#6121-switch-ptp-port-mode)
      - [6.1.2.2 ptp configuration](#6122-ptp-configuration)
    - [6.1.3 ASIC\_DB](#613-asic_db)
      - [6.1.3.1 Switch Port PTP Mode Configuration](#6131-switch-port-ptp-mode-configuration)
    - [6.1.4 STATE\_DB](#614-state_db)
      - [6.1.4.1 PTP Status](#6141-ptp-status)
    - [6.1.5 COUNTERS\_DB](#615-counters_db)
      - [6.1.4.1 PTP Port Statistics](#6141-ptp-port-statistics)
- [7 Testing](#7-testing)

### Revision


| Rev | Date | Author     | Change Description |
| --- | ---- | ---------- | ------------------ |
| 0.1 | 2026-04-29 | Maike Geng | Initial edition    |
| 0.2 | 2026-05-05 | Maike Geng | Review and merge in data models   |


### About this manual

This document provides an overview of the PTPv2 feature in SONiC.

### Scope

This document is the high level design document for running a SONiC switch as a PTPv2 boundary/ordinary/transparent clock.  It provides an overview of feature configuration and operation and its flow through SONiC and its sub-systems.

### Abbreviations


| Term  | Meanings                                                             |
| ----- | -------------------------------------------------------------------- |
| ASIC  | Application-Specific Integrated Circuit                              |
| BC    | Boundary Clock                                                       |
| BMCA  | Best Master Clock Algorithm                                          |
| DB    | Database                                                             |
| CLI   | Command-line Interface                                               |
| NTP   | Network Time Protocol                                                |
| OC    | Ordinary Clock                                                       |
| pmc   | PTP Management Client; a linux-ptp executable                        |
| PHC   | PTP Hardware Clock; Linux timing synchronization infrastructure |
| PTP   | Precision Time Protocol                                              |
| PTPv2 | PTP Version 2; IEEE-1588 2008 specification with 2019 enhancements   |
| ptp4l | PTP daemon for Linux; a linux-ptp executable                         |
| SAI   | Switch Abstraction Interface                                         |
| SONiC | Software for Open Networking in the Cloud                            |
| TC    | Transparent Clock                                                    |
| UDS   | Unix Domain Socket                                                   |
| YANG  | Yet Another Next Generation                                          |


# 1 Introduction

Certain distributed applications require good time synchronization across nodes.  For applications that require time synchronization on the order of ten milliseconds, NTP can run on nodes and may already be sufficient.  For applications that require time synchronization on the order of milliseconds or better, PTPv2 is the industry-standard network protocol for achieving such time synchronization.  In PTPv2 deployments, running PTP boundary clocks or PTP transparent clocks on network switches between nodes and authoritative time sources will improve the accuracy and the scalability of the solution.  By enabling the PTP feature and applying PTP configurations, SONiC switches will be able to operate as PTPv2 clocks.

# 2 Feature Design

PTP is an [optional feature application](../optional-feature-control/Optional-Feature-Control.md) that can be enabled or disabled.  When the PTP feature is enabled, SONiC will launch its PTP container on a per-ASIC namespace basis.  The PTP container operates as a PTPv2 boundary, ordinary, or transparent clock, depending on the configuration. The PTP protocol stack is handled by open-source ptp4l.  The PTP feature implements PTPv2.1 and will not support PTPv1 protocol.  It works on ports attached to ASICs and is not applicable to out-of-band management ports.  ASICs should support hardware timestamping and provide required kernel drivers/firmware.

## 2.1 Operational Flow

```mermaid
---
title: PTP operational flow
---
  flowchart TB
    subgraph input[User and Management]
      cli[CLI]
      netconf[NetConf Interface]
      restconf[RestConf Interface]
    end

    subgraph SONIC
      subgraph redis[Redis Database]
        direction TB
        config_db[(CONFIG_DB)]
        state_db[(STATE_DB)]
        appl_db[(APPL_DB)]
        counter_db[(COUNTERS_DB)]
        asic_db[(ASIC_DB)]
      end

      subgraph ptp[PTP container]
        appcfg[PTP app manager]
        ptp4l[ptp4l]
        telemetry_[telemetry feed]

        appcfg== launches ==>ptp4l
        appcfg== launches ==>telemetry_
        ptp4l-->|polled by|telemetry_
      end

      subgraph syncd container
        syncd[syncd]
        sai[[SAI]]

        syncd-- calls -->sai
      end

      subgraph swss_service[swss container]
        subgraph orchagent
          switchorch[[switchorch]]
        end
      end
    end

    subgraph kernel[Linux Kernel]
      eth_dev([Ethernet Device])
      phc_dev([PHC Device])
      eth_dev-->|associated with|phc_dev
    end

    subgraph hardware[hardware components]
      phy(PHY)
      asic_dev{{ASICs}}
      phy<==>|IP packets|asic_dev
    end

    config_db-- subscription -->appcfg
    appcfg-- writes -->appl_db
    appl_db-- subscription -->switchorch
    switchorch-- writes -->asic_db
    asic_db-- subscription -->syncd
    sai-- programs ---asic_dev
    asic_dev<==>|IP packets|eth_dev
    input-->config_db
    input<-->state_db
    input<-->counter_db
    telemetry_-- writes -->state_db
    telemetry_-- writes -->counter_db
    ptp4l<==>|PTP packets|eth_dev
    ptp4l<-->|programs and queries|phc_dev
```


## 2.2 PTP Container

The PTP protocol stack is processed in the PTP container.  When SONiC launches the PTP service, one instance of the PTP container runs under each ASIC namespace.

When a PTP container starts, it launches an instance of the PTP app manager, which will read the SONiC configuration from CONFIG_DB.  PTP configuration consists of a base ptp4l configuration that all PTP containers share and configuration for Ethernet ports.   The PTP app manager will combine configuration for Ethernet ports that are applicable to the ASIC namespace with the base ptp4l configuration and write a /etc/ptp4l.cfg inside the container.  When the /etc/ptp4l.cfg is written, the PTP app manager will start the ptp4l process.  After the ptp4l process starts, the PTP app manager will start a telemetry feed process.  The telemetry feed process will regularly query the ptp4l process for status and statistics through ptp4l's UDS/pmc interface and push all status and statistics into STATE_DB and COUNTERS_DB.

The PTP app manager will continue to listen to CONFIG_DB for changes to configuration.  When PTP app manager receives an update, the app manager will regenerate the /etc/ptp4l.cfg file, and relaunches the ptp4l and telemetry feed processes.  On-the-fly configuration is not supported.

The ptp4l expects all interfaces are associated with one single PHC, and in BC and OC operation, the ptp4l can freely adjust the PHC as a slave clock.  This operational model requires each ASIC to have one independently adjustable PHC.  This one PHC must be associate with all ports attached to the ASIC.

## 2.3 Configuration Templates

For bootstrapping ptp4l.cfg, the PTP app manager will have templates for well-defined target use cases.  The jinja template will be able to incorporate network topology from the CONFIG_DB, minigraph, platform-specific parameters from platform.json, and produce working ptp4l.cfg files for ptp4l operation.

There will be configuration template for Boundary Clock operation using G.8275.2 profile.

## 2.4 Time Distribution Network Variants

The ptp4l process may operate as boundary clock, ordinary clock, or transparent clock with the ptp4l configuration file.  The ptp4l process is programmed to be able to exchange ptp packets with L2 transport, unicast IPv4 or IPv6 transport, or multicast IPv4 or IPv6 transport.  There is no development effort in PTP feature associated with supporting these variations of operation.  However, due to SONiC capabilities and limitations and the non-trivial need for testing and testing resources, validation of these operation variants will be introduced on an as-needed basis associated with well-defined target use cases.

### 2.4.1 Ordinary Clock

Ordinary Clock operation mode is when the SONiC network device recovers time from upstream master.

### 2.4.2 Boundary Clock

Boundary Clock operation mode is when the SONiC network device recovers time from upstream master and serves as potential master to other network devices.

### 2.4.3 Transparent Clock

Transparent Clock operation mode is when the SONiC network device timestamps PTP event messages.  Transparent clocks can be configured to operate in either E2E mode or P2P mode.

There are currently no target use cases that require this feature.

### 2.4.4 IPv4/IPv6 Unicast transports

PTP packets may be transported with unicast IPv4 or IPv6 packets.

### 2.4.5 IPv4/IPv6 Multicast transports

PTP packets may transmit certain PTP messages using multicast IPv4 or IPv6 packets.  Using this transport mode reduces packet load on the upstream master clocks, but requires switch devices in the network to support multicast routing and track multicast memberships.

### 2.4.6 L2 transport

PTP packets may transmit PTP packets with L2 addresses.

## 2.5 Hardware Features Support

Different PTPv2 deployments can have orders of magnitude differences in the accuracy of time synchronization, ranging from sub-millisecond accuracy of software timestamping to sub-nanosecond accuracy of White Rabbit PTP deployments.  The deployments with higher accuracy have Ethernet hardware with hardware features that can minimize the errors or measure errors to enable algorithms to remove them.  Software features that enable these hardware features are optional and may not be applicable to all PTPv2 deployments.  Thus the PTP feature can become deployable before support for any or all of these hardware features are supported in SONiC.

### 2.5.1 Hardware Timestamping Configuration

PTPv2 can use Ethernet ports which can be configured for hardware timestamping. Hardware timestamping can be configured to operate in one-step hardware timestamping mode or two-step hardware timestamping mode.

### 2.5.2 Static Delay Asymmetry Configuration

SONiC switch vendor may statically measure delay asymmetry on Ethernet ports in their system and provide values for fine tuning purposes.

There are currently no target use cases that require this feature, and no further design details have been defined.

### 2.5.3 SyncE

Operating in conjunction with SyncE is part of gPTP/802.1AS specification.

There are currently no target use cases that require this feature, and no further design details have been defined.

### 2.5.4 G.8275.1 Support

G8275.1 requires support for SyncE, uses alternate BMCA logic, and can recover from two different grandmaster.

There are currently no target use cases that require this feature, and no further design details have been defined.

## 2.6 Chassis/Multi-ASIC support

A chassis based system has multiple linecards with multiple ASICs in each line card.  Since each ASIC runs in different namespace, there will be a PTP container running in each namespace.  On these systems, there will be an internal ptp session running between namespaces over the recycle port.  The same applies to VOQ-based pizza boxes with multiple ASICs connected with fabric. 

Some multi-device/multi-ASIC clock systems may not adhere to this assumption and have PHCs for multi-ASICs that are coupled together.  Phase 2 may require support for this kind of hardware, however no design details have been defined and is TBD.

# 3 Requirements Roadmap

Development of the PTP feature will proceed in phases.  Software support for hardware features will be developed on an as-needed basis with well-defined target use cases.

## 3.1 Phase 1

Phase 1 will support G.8275.2 profile using one-step hardware timestamping on single-ASIC pizza box that have the required hardware capability.  Both IPv4 and IPv6 over UDP and BC and OC modes will be supported. Phase 1 is targeted for 202611 release.

## 3.2 Phase 2

Testing will validate the PTP feature on multi-device multi-ASIC SONiC network devices, with everything else remaining the same, running as PTPv2 BC, over unicast IPv4 transport, with default IEEE-1588 profile, using one-step hardware timestamping.

# 4 Configuration

The following new commands will be introduced in SONiC

Enable/Disable PTP feature on a particular device:
```bash
config feature state ptp enabled/disabled
```
The following commands will have an entry for ptp:
```bash
show feature config 
show feature status
```
PTP Configuration Commands
Create a unicast-master-table and add IP host addresses of potential masters
```bash
config ptp unicast-master-table add/remove <table-name>
config ptp unicast-master-table ip add/remove <table-name> <ipv4/ipv6 address>
```
Enable PTP on a port and associate a unicast host table if required
```bash
config ptp interface add <interface-name> [<table-name>][--unicast-listen]
config ptp interface remove <interface-name>
```
Global PTP configuration:
```bash
config ptp domain-number <domain number>
config ptp sync-interval <interval>
config ptp announce-interval <interval>
```
Show which ports have PTP enabled/disabled:
```bash
show ptp port status
```
Shows ptp status:
```bash
show ptp status
```
Shows ptp interface counters:
```bash
show ptp counters <interface-name>
```
Clears ptp counters on all ports:
```bash
sonic-clear ptp counters
```

# 5 Module Design

## 5.1 PTP Container

The PTP Container is a new container.  It has three processes, PTP app manager, ptp4l, and telemetry feed.

The PTP app manager is a new process that interfaces with SONiC databases, prepares ptp4l configuration and launches ptp4l.

The ptp4l processes is [open-source software](git://git.code.sf.net/p/linuxptp/code) from the Linux PTP project.  It implements the PTP for Linux using Linux SO_TIMESTAMPING socket option and Linux PTP Hardware Clock subsystem.

The telemetry feed is new process that will pool ptp4l through its UDS interface for status and statistics.  It will update SONiC databases, STATE_DB and COUNTERS_DB, for status and statistics.

## 5.2 orchagent

Switch orch will recognize ptp_mode attribute in switch objects and translate it into SAI_SWITCH_ATTR_PORT_PTP_MODE.  There will be a copp rule added to handle PTP packets.

## 5.3 Syncd Updates

The syncd is an existing process that subscribes to ASIC_DB and applies changes to ASICs through SAI calls.

## 5.4 SAI Interface

The SAI is an existing library component with vendor-specific implementation. SAI already defines attributes for PTP modes in switch and port objects and no changes are necessary.

## 5.5 SAI implementations and ASIC Device Driver Updates

The SAI implementation and ASIC device driver is an existing vendor-specific component.  To support the PTP feature, the ASIC device driver creates and maintains Linux Ethernet devices that have associated Linux PHC devices.  The vendor-specific SAI implementation with support for SAI_SWITCH_ATTR_PORT_PTP_MODE on switch objects will be invoked to program the ASIC for PTP timestamping operation.

## 5.6 Linux Ethernet Device Update

The Ethernet device is an existing standard Linux device infrastructure object representing Ethernet ports. When applicable, the Ethernet device will advertise hardware timestamping capability and have an associated Linux PHC device.  For hardware timestamping support, the Linux Ethernet devices will advertise SOF_TIMESTAMPING_TX_HARDWARE, SOF_TIMESTAMPING_RX_HARDWARE, and SOF_TIMESTAMPING_RAW_HARDWARE capabilities.  ptp4l interacts directly with the Linux Ethernet device.

## 5.7 PHC Device

The PHC device is a new standard Linux infrastructure object representing PTP clocks. ptp4l interacts directly with the Linux PHC device.

# 6 Data Model

## 6.1 SONiC DBs

### 6.1.1 Config_DB

#### 6.1.1.1 Feature Config

Feature config follows [optional feature standard](../optional-feature-control/Optional-Feature-Control.md) and its data model for defining a SONiC feature.  We introduce a new key for the PTP feature.

```
FEATURE|ptp
     {
          "auto_restart": ("enabled"|"disabled"),
          "delayed": "False",
          "has_global_scope": "False",
          "has_per_asic_scope": "True"
          "state": ("enabled"|"disabled"),
     }
```

The PTP feature may be enabled or disabled in the "state" key.  Default is "disabled".  Auto-restart of the PTP feature may be enabled or disabled in "auto_restart" key.  Default is "enabled".

#### 6.1.1.2 Port Config

PTP feature adds a field into switch config object.  Default is "none".

```
SWITCH|switch
{
+     "ptp-mode": ("none"|"one-step|two-step"),
}
```
#### 6.1.1.3 PTP Config
```
PTP_UNICAST_MASTER_TABLE|{table-name}|<ip-addar>
  family = ipv4

PTP_Interface|{if-name}
  unicast_master_table=<table-name>
  unicast_listen=1
```
### 6.1.2 APPL_DB

Application DB of PTP is per ASIC namespace.  There changes to keys for PTP feature in the asic namespace.

#### 6.1.2.1 Switch ptp port mode
PTP feature adds a field into switch object.  Default is "none".

```
SWITCH_TABLE:switch
{
+     "ptp-mode": ("none"|"one-step|two-step"),
}
```

#### 6.1.2.2 ptp configuration
This is TBD.

### 6.1.3 ASIC_DB
There are existing SAI definition for PTP timestamping mode and these existing SAI definitions are used.

#### 6.1.3.1 Switch Port PTP Mode Configuration

```
ASIC_STATE:SAI_OBJECT_TYPE_SWITCH:oid:{{oid value}}
{
     "SAI_SWITCH_ATTR_PORT_PTP_MODE": ("SAI_PORT_PTP_MODE_NONE"|"SAI_PORT_PTP_MODE_SINGLE_STEP_TIMESTAMP"|"SAI_PORT_PTP_MODE_TWO_STEP_TIMESTAMP")
}

```
### 6.1.4 STATE_DB

### 6.1.4.1 PTP Status
There is a new state object adopted from [IETF RFC 8575](https://datatracker.ietf.org/doc/rfc8575/).
```
PTP_GROUP|ptp
{
  "instance-list": [
    {
      "instance-number": uint32,
      "default-ds": {
        "two-step-flag": ("True"|"False"),
        "clock-identity-type": string,
        "number-ports": uint16,
        "clock-quality": {
          "clock-class": uint8,
          "clock-accuracy": uint8,
          "offset-scaled-log-variance": uint16,
        },
        "priority1": uint8,
        "priority2": uint8,
        "domain-number": uint8,
        "slave-only": ("True"|"False"),        
      },
      "current-ds": {
        "steps-removed": uint8,
        "offset-from-master": string,
        "mean-path-delay": string,
      },
      "parent-ds": {
        "parent-port-identity": {
          "clock-identity": string,
          "port-number": uint16,
        },
        "parent-stats": ("True"|"False"),
        "observed-parent-offset-scaled-log-variance": uint16,
        "observed-parent-clock-phase-change-rate": int32,
        "grandmaster-identity": string,
        "grandmaster-clock-quality": {
          "clock-class": uint8,
          "clock-accuracy": uint8,
          "offset-scaled-log-variance": uint16,
        },
        "grandmaster-priority1": uint8,
        "grandmaster-priority2": uint8,
      },
      "time-properties-ds": {
        "current-utc-offset-valid": ("True"|"False"),
        "current-utc-offset": int16,
        "leap59": ("True"|"False"),
        "leap61": ("True"|"False"),
        "time-traceable": ("True"|"False"),
        "frequency-traceable": ("True"|"False"),
        "ptp-timescale": ("True"|"False"),
        "time-source": uint8,
      },
      "port-ds-list": [
        {
          "port-number": uint16,
          "port-state": uint8,
          "underlying-interface": string,
          "log-min-delay-req-interval": int8,
          "peer-mean-path-delay": string,
          "log-announce-interval": int8,
          "announce-receipt-timeout": uint8,
          "log-sync-interval": int8,
          "delay-mechanism": string,
          "log-min-pdelay-req-interval": int8,
          "version-number": uint8,
        },
      ]
    },
  ]
}
```

### 6.1.5 COUNTERS_DB

### 6.1.4.1 PTP Port Statistics

There is a new statistic object for ptp port statistics.  The key and the contents are currently TBD.

# 7 Testing

Testing will be automated to validate the feature and deployment models found in each phase.  The testing HLD will be a separate document and is currently TBD.
As per [phase 1](#31-phase-1) and [phase 2](#32-phase-2), testing will be limited to the targeted use cases.
