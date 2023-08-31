# SRv6 Path Tracing Midpoint #

## Table of Content 

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
    - [Functional requirements](#functional-requirements)
    - [Configuration and Management Requirements](#configuration-and-management-requirements)
- [Architecture Design](#architecture-design)
- [High-Level Design](#high-level-design)
    - [SONiC CLI Changes](#sonic-cli-changes)
        - [CLI Configuration Commands](#cli-configuration-commands)
        - [CLI Show Commands](#cli-show-commands)
    - [CONFIG_DB Changes](#config_db-changes)
    - [PortSyncd Changes](#portsyncd-changes)
    - [PortMgrd Changes](#portmgrd-changes)
    - [APPL_DB Changes](#APPL_DB-changes)
    - [PortsOrch OrchAgent Changes](#portsorch-orchagent-changes)
    - [ASIC_DB Changes](#asic_db-changes)
- [SAI API](#sai-api)
- [Testing Requirements/Design](#testing-requirementsdesign)
    - [Unit Test cases](#unit-test-cases)
        - [Test cases for configuration CLI commands](#test-cases-for-configuration-cli-commands)
        - [Test cases for configuration show commands](#test-cases-for-configuration-show-commands)
        - [Test cases for PortMgr](#test-cases-for-portmgr)
        - [Test cases for OrchAgent](#test-cases-for-orchagent)
    - [System Test cases](#system-test-cases)
- [Open/Action items](#openaction-items)
- [References](#references)

## Revision  

| Rev  |   Date    |      Author                         | Change Description      |
| :--: | :-------: | :---------------------------------: | :---------------------: |
| 0.1  | 22/8/2023 | Carmine Scarpitta, Ahmed Abdelsalam |  Initial version        |

## Scope  

This document describes the requirements, architecture, and configuration details of the SRv6 Path Tracing Midpoint feature in SONiC.

## Definitions/Abbreviations 

| **Term**                 | **Definition**                                                                                      |
|--------------------------|-----------------------------------------------------------------------------------------------------|
| PT                       | Path Tracing                                                                                        |
| MCD                      | Midpoint Compressed Data.  Information that every transit router adds to the packet for PT purposes |
| HbH-PT                   | IPv6 Hop-by-Hop Path Tracing Option used for PT. It contains a stack of MCDs                        |
| PT Source                | A Source node that starts a PT Probing Instance and generates PT probes                             |
| PT Midpoint              | A transit node that performs plain IPv6 forwarding (or SR Endpoint processing) and in addition records PT information in the HbH-PT |
| PT Sink                  | A node that receives PT probes sent from the SRC containing the information recorded by every PT Midpoint along the path, and forwards them to a regional collector after recording its PT information |
| RC                       | Regional collector that receives PT probes, parses, and stores them in TimeSeries Database. It uses the PT information to construct the packet delivery path as well as the timestamp at each node |

The Path Tracing terminologies are defined in [draft-filsfils-spring-path-tracing](https://www.ietf.org/archive/id/draft-filsfils-spring-path-tracing-04.html#name-terminology).

## Overview 

Path Tracing provides a record of the packet path as a sequence of interface ids. In addition, it provides a record of end-to-end delay, per-hop delay, and load on each egress interface along the packet delivery path. 

Path Tracing supports fine grained timestamp. It has been designed for linerate hardware implementation in the base pipeline.

Path Tracing enjoys a very rich ecosystem both from Vendor and Open-Source point of view. 

Path Tracing is supported across many HW ASIC including Cisco Silicon One, Cisco Light Speed, Broadcom Jericho, Broadcom Jericho2, Marvell and many others. 

Path Tracing has also a very opensource ecosystem that includes the Linux Kernel, FD.io VPP, an open P4 implementation, and support in applications such as Wireshark and TCPDump.

The list routing of platforms that have successfully participated in the Path Tracing interop testing are reported in 
[draft-filsfils-spring-path-tracing](https://www.ietf.org/archive/id/draft-filsfils-spring-path-tracing-04.html#name-implementation-status).

## PT Midpoint 

Each PT Midpoint node on the packet path records a tiny piece of information known as Midpoint Compressed Data (MCD). 

The Midpoint Compressed Data (MCD) contains the outgoing interface ID, outgoing (truncated) timestamp, and the load of the outgoing interface.

Every interface of the PT Midpoint is assigned an interface ID and timestamp template. The timestamp template defines how to trunacte the timestamp (i.e., which bits of the timestamp are selected). 

In this document, we provide the SONiC High Level Design (HLD) to program the Path Tracing Interface ID and timestamp template. 

The SAI Port object has been extended with two new attributes for the [Interface ID](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h#L2346) and the [timestamp template](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h#L2355).

The SAI Port header defines [four different timestamp templates](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h#L507C14-L507C53) as follows: 

| Name       | Description                          |
| :--------: | :----------------------------------: |
| template1  | Select bits 08-15 from the timestamp |
| template2  | Select bits 12-19 from the timestamp |
| template3  | Select bits 16-23 from the timestamp |
| template4  | Select bits 20-27 from the timestamp |


## Requirements

### Functional requirements

This feature provides the following high-level functional requirements:

- Configuration of the Path Tracing *Interface ID* and *Timestamp Template* of a physical port
- Verification of the configured Path Tracing *Interface ID* and *Timestamp Template* of a physical port

### Configuration and Management Requirements

- Extend SONiC CLI to support the configuration of the Path Tracing *Interface ID* and *Timestamp Template* of a physical port
- Extend SONiC CLI to support the verification of the configured Path Tracing *Interface ID* and *Timestamp Template* of a physical port

## Architecture Design 

This document describes the changes required to support the PT Midpoint in SONiC.

The overall architecture of SONiC is not modified. Supporting the PT Midpoint functionality in SONiC does not require any additional components.

The only requirement is to extend some components (namely SONiC CLI and OrchAgent) to support the configuration and validation of port parameters required by the PT Midpoint functionality.

## High-Level Design 

The following diagram shows the steps required to configure the PT Midpoint feature in SONiC:
<br> <br>

![SRv6 Path Tracing Midpoint Sequence Diagram](images/srv6_path_tracing_midpoint_sequence_diagram.png "SRv6 Path Tracing Midpoint Sequence Diagram").

(1) The user configures the *PT Interface ID* and *PT Timestamp Template* of a physical port via the SONiC CLI.

(2) The SONiC CLI uses the _portconfig_ script to inject the PT Interface ID and PT Timestamp Template into the PORT table in CONFIG_DB.

(3) portmgrd receives a PORT update notification (portmgrd is an CONFIG_DB subscriber).

(4) portmgrd inject the PT Interface ID and PT Timestamp Template into the PORT_TABLE in APPL_DB.

(5) PortsOrch receives a PORT_TABLE update notification (PortsOrch is an APPL_DB subscriber).

(6) PortsOrch invokes the sairedis `set_port_attribute()` APIs to set the port PT attributes including PT Interface ID, PT Timestamp Template, PT TAM Object. The port PT attributes are injected  into the ÀSIC_DB.

The next subsections describe the changes required to support the PT Midpoint HLD described above. 

### SONiC CLI Changes

#### CLI Configuration Commands

The existing `config interface` command is extended by introducing a new subcommand `pt` that allows users to configure the Interface ID and Timestamp Template parameters required for the PT Midpoint functionality. The Timestamp Template is optional. The default template is *template3*.

```
admin@sonic:~# config interface pt <interface_name> <pt_interface_id> [pt_timestamp_template]

    <interface_name>: interface name 
    <pt_interface_id>: Path Tracing Interface ID (0-4095)
    [pt_timestamp_template]: Path Tracing timestamp template (optional)
        Supported templates {template1, template2, template3, template4}
            template1: timestamp[08:15]
            template2: timestamp[12:19]
            template3: timestamp[16:23]
            template4: timestamp[20:27]
        Default: template3
```

**Example 1:**

```
admin@sonic:~# config interface pt Ethernet8 128
```

The above command assigns Ethernet8 a Path Tracing Interface ID of 128 and a Timestamp Template template3 (default).

**Example 2:**

```
admin@sonic:~# config interface pt Ethernet9 129 template2
```

The above command assigns Ethernet9 a Path Tracing Interface ID of 129 and a Timestamp Template template2.

#### CLI Show Commands

The existing `show interfaces` command is extended by introducing a new subcommand `pt` that allows users to verify the current PT Midpoint configuration (i.e., the Interface ID and Timestamp Template parameters).

```
admin@sonic:~$ show interfaces pt [interface_name]
```

**Example 1** - Show PT Midpoint configuration for all interfaces:

```
admin@sonic:~$ show interfaces pt

      Interface            Alias    Oper    Admin    PT Interface ID   PT Timestamp Template
---------------  ---------------  ------  -------  -----------------  ---------------------- 
      Ethernet8   fortyGigE0/0/8      up       up                128               template3
      Ethernet9   fortyGigE0/0/9      up       up                129               template2 
```

**Example 2** - Show PT Midpoint configuration for interface Ethernet8:

```
admin@sonic:~$ show interfaces pt Ethernet9

      Interface            Alias    Oper    Admin    PT Interface ID   PT Timestamp Template
---------------  ---------------  ------  -------  -----------------  ---------------------- 
      Ethernet8   fortyGigE0/0/9      up       up                129               template2
```

### CONFIG_DB Changes

The configuration parameters for the port are stored in the PORT table in CONFIG_DB.

Currently, the PORT table has the following schema:

```
;Configuration for layer 2 ports
key                 = PORT|ifname   ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
admin_status        = "down" / "up" ; admin status
lanes               = list of lanes ; (need format spec???)
mac                 = 12HEXDIG      ;
alias               = 1*64VCHAR     ; alias name of the port used by LLDP and SNMP, must be unique
description         = 1*64VCHAR     ; port description
speed               = 1*6DIGIT      ; port line speed in Mbps
mtu                 = 1*4DIGIT      ; port MTU
fec                 = 1*64VCHAR     ; port fec mode
autoneg             = BIT           ; auto-negotiation mode
```

To support PT Midpoint in SONiC, two new attributes `pt_interface_id` and `pt_timestamp_template` are added to the PORT table schema.

```
;Configuration for layer 2 ports
key                   = PORT|ifname   ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
...
pt_interface_id       = 1*4DIGIT      ; Path Tracing Interface ID (0-4095)
pt_timestamp_template = "template1" / "template2" / "template3" / "template4"; Path Tracing Timestamp Template
```

### PortSyncd Changes

PortSyncd is an existing daemon in SWSS container that reads the port configurations from configDB on boot and pushes them into APPL_DB. Then, Portsyncd listens on Netlink messages to make sure interfaces are ready before other subsystem can continue to work on port-related objects.

There is no PortSyncd modification required to support PT Midpoint as PortSyncd propagates all port attributes from CONFIG_DB PORT table to APPL_DB PORT_TABLE. Propagated attributes also include the new PT Interface ID and Timestamp Template attributes required for PT Midpoint.

### PortMgrd Changes

PortMgrd is an existing daemon in SWSS container that monitors operations in CONFIG_DB on the PORT table.

There is no PortMgrd modification required to support PT Midpoint as PortMgrd propagates all port attributes from CONFIG_DB PORT table to APPL_DB PORT_TABLE. Propagated attributes also include the new PT Interface ID and Timestamp Template attributes required for PT Midpoint.

### APPL_DB Changes

The configuration parameters for the port are stored in the PORT_TABLE in APPL_DB.

Currently, the PORT_TABLE has the following schema:

```
;Defines layer 2 ports
;In SONiC, Data is loaded from configuration file by portsyncd
key                 = PORT_TABLE:ifname    ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
admin_status        = "down" / "up"        ; admin status
oper_status         = "down" / "up"        ; oper status
lanes               = list of lanes ; (need format spec???)
mac                 = 12HEXDIG      ;
alias               = 1*64VCHAR     ; alias name of the port used by LLDP and SNMP, must be unique
description         = 1*64VCHAR     ; port description
speed               = 1*6DIGIT      ; port line speed in Mbps
mtu                 = 1*4DIGIT      ; port MTU
fec                 = 1*64VCHAR     ; port fec mode
autoneg             = BIT           ; auto-negotiation mode
preemphasis         = 1*8HEXDIG *( "," 1*8HEXDIG) ; list of hex values, one per lane
idriver             = 1*8HEXDIG *( "," 1*8HEXDIG) ; list of hex values, one per lane
ipredriver          = 1*8HEXDIG *( "," 1*8HEXDIG) ; list of hex values, one per lane
```

To support PT Midpoint in SONiC, two new attributes `pt_interface_id` and `pt_timestamp_template` are added to the PORT_TABLE schema.

```
;Defines layer 2 ports
key                   = PORT_TABLE:ifname    ; ifname must be unique across PORT,INTF,VLAN,LAG TABLES
...
pt_interface_id       = 1*4DIGIT      ; Path Tracing Interface ID (0-4095)
pt_timestamp_template = "template1" / "template2" / "template3" / "template4"; Path Tracing Timestamp Template
```

### PortsOrch (OrchAgent) Changes

PortsOrch is an existing component of the OrchAgent daemon in the SWSS container. PortsOrch monitors operations on Port related tables in APPL_DB and converts those operations into SAI commands to manage port entries.

PortsOrch is extended to support PT Midpoint. It  invokes the sairedis `set_port_attribute()` APIs to set the port PT attributes including PT Interface ID, PT Timestamp Template, PT TAM Object. The port PT attributes are injected  into the ÀSIC_DB.

## SAI API 

The SAI Port object has been extended with two new attributes [SAI_PORT_ATTR_PATH_TRACING_INTF](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h#L2346) and the [SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE](https://github.com/opencomputeproject/SAI/blob/master/inc/saiport.h#L2355) to support PT Midpoint. 

```
    /**
    * @brief Attribute data for #SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE
    */
    typedef enum _sai_port_path_tracing_timestamp_type_t
    {
        /** Timestamp nanosecond bits [8:15] */
        SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_8_15,

        /** Timestamp nanosecond bits [12:19] */
        SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_12_19,

        /** Timestamp nanosecond bits [16:23] */
        SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_16_23,

        /** Timestamp nanosecond bits [20:27] */
        SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_20_27,

    } sai_port_path_tracing_timestamp_type_t;

    /**
     * @brief Configure path tracing interface id
     *
     * @type sai_uint16_t
     * @flags CREATE_AND_SET
     * @isvlan false
     * @default 0
     */
    SAI_PORT_ATTR_PATH_TRACING_INTF,

    /**
     * @brief Configure path tracing timestamp template
     *
     * @type sai_port_path_tracing_timestamp_type_t
     * @flags CREATE_AND_SET
     * @default SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_16_23
     */
    SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE,
```

In addition, the SAI TAM INT object has been extended with one new attribute [SAI_TAM_INT_TYPE_PATH_TRACING](https://github.com/opencomputeproject/SAI/blob/1eceedf7609841c3e08075d60fdc8d76f5dc3421/inc/saitam.h#L482). 

```
/**
 * @brief TAM INT types
 */
typedef enum _sai_tam_int_type_t
{
    /**
     * @brief INT type IOAM
     */
    SAI_TAM_INT_TYPE_IOAM,

    /**
     * @brief INT type IFA1
     */
    SAI_TAM_INT_TYPE_IFA1,

    /**
     * @brief INT type IFA2
     */
    SAI_TAM_INT_TYPE_IFA2,

    /**
     * @brief INT type P4 INT v1
     */
    SAI_TAM_INT_TYPE_P4_INT_1,

    /**
     * @brief INT type P4 INT v2
     */
    SAI_TAM_INT_TYPE_P4_INT_2,

    /**
     * @brief Direct Export (aka postcard)
     */
    SAI_TAM_INT_TYPE_DIRECT_EXPORT,

    /**
     * @brief Telemetry data at the end of the packet
     */
    SAI_TAM_INT_TYPE_IFA1_TAILSTAMP,

    /**
     * @brief INT type Path Tracing
     */
    SAI_TAM_INT_TYPE_PATH_TRACING,

} sai_tam_int_type_t;

```

These attributes allows to enable PatH Tracing on the interface and set the PT Interface ID and PT Timestamp Template for a SAI_OBJECT_TYPE_PORT. The new SAI attributes is merged in SAI in [PR#1841](https://github.com/opencomputeproject/SAI/pull/1841#) and will be will be available in SAI 1.13 release.

		
## Testing Requirements/Design  

### Unit Test cases  

#### Test cases for configuration CLI commands

A new unit test `config_int_pt_test.py` is created to verify the new `config interface pt ...` CLI command introduced in SONiC.

This test includes two test cases:

- `test_interface_pt_interface_id_check` provides a valid PT Midpoint configuration to SONiC via the CLI and verifies that the SONiC CLI processes the command correctly (i.e., no errors are returned).
- `test_interface_invalid_pt_interface_id_check` provides an invalid Interface ID and Timestamp Template to SONiC and verifies that the SONiC CLI rejects the configuration.

#### Test cases for configuration show commands

The existing `intfutil_test.py` is extended to verify the new `show interfaces pt [interface_name]` CLI command introduced in SONiC.

Two new test cases are added:

- `test_show_interfaces_pt_status` verifies that the `show interfaces pt` returns the expected output.
- `test_show_interfaces_pt_Ethernet9_status` verifies that the `show interfaces pt Ethernet9` returns the expected output.

#### Test cases for PortMgr

To validate PT Midpoint, two test cases are added to the existing PortMgr unit test (`portmgr_ut.cpp`):

- `ConfigurePortPTDefaultTimestampTemplate` writes a port configuration to the CONFIG_DB (without specifying the PT Timestamp Template) and verifies that PortMgr correctly propagates the PT Midpoint parameters to the APP_DB.
- `ConfigurePortPTTimestampTemplate2` writes a port configuration to the CONFIG_DB (with a specific PT Timestamp Template) and verifies that PortMgr correctly propagates the PT Midpoint parameters to the APP_DB.

#### Test cases for OrchAgent

To validate PT Midpoint, two test cases are added to the existing PortsOrch unit test (`portsorch_ut.cpp`):

- `PortPTConfigDefaultTimestampTemplate` writes a port configuration to the APPL_DB (with PT Interface ID non-zero and default PT Timestamp Template) and verifies that PortsOrch propagates the PT Midpoint parameters to the ASIC_DB.
- `PortPTConfigTimestampTemplate2` writes a port configuration to the APPL_DB (with PT Interface ID non-zero and PT Timestamp Template specified) and verifies that PortsOrch correctly propagates the PT Midpoint parameters to the ASIC_DB.

### System Test cases

To validate PT Midpoint, two test cases are added to the existing `tests/test_port.py` (in the `sonic-swss` repository):

- `test_PortPtDefaultTimestampTemplate` writes a port configuration to the CONFIG_DB (with PT Interface ID non-zero and default PT Timestamp Template) and verifies that APPL_DB and ASIC_DB are updated correctly.
- `test_PortPtTimestampTemplate2` writes a port configuration to the CONFIG_DB (with PT Interface ID non-zero and PT Timestamp Template specified) and verifies that APPL_DB and ASIC_DB are updated correctly.

## Open/Action items

The PT Midpoint feature proposed in this document depends on the following PRs:

- Add CLI commands for SRv6 Path Tracing: https://github.com/sonic-net/sonic-utilities/pull/2983.
- [orchagent] Add support for SRv6 Path Tracing Midpoint: https://github.com/sonic-net/sonic-swss/pull/2903

## References

- [Path Tracing in SRv6 Networks](https://www.ietf.org/archive/id/draft-filsfils-spring-path-tracing-04.html)
- [SAI-Proposal-SRv6-Path-Tracing](https://github.com/opencomputeproject/SAI/blob/master/doc/SAI-Proposal-SRv6-Path-Tracing.md)
