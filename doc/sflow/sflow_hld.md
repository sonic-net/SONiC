# sFlow High Level Design
### Rev 0.3
## Table of Contents

## 1. Revision 
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
v0.1	 |05/01/2019	|Padmanabhan Narayanan	| Initial version
v0.2    |05/20/2019  |Padmanabhan Narayanan      | Updated based on internal review comments
v0.3    |06/11/2019  |Padmanabhan Narayanan      | Update CLIs, remove sflowcfgd 

## 2. Scope
This document describes the high level design of sFlow in SONiC

## 3. Definitions/Abbreviations

Definitions/Abbreviation|Description
------------------------|-----------
SAI| Switch Abstraction Interface
NOS| Network Operating System
OID| OBject Identifier

## 4. Overview

sFlow (defined in https://sflow.org/sflow_version_5.txt) is a standard-based sampling technology the meets the key requirements of network traffic monitoring on switches and routers. sFlow uses two types of sampling:

* Statistical packet-based sampling of switched or routed packet flows to provide visibility into network usage and active routes
* Time-based sampling of interface counters.

The sFlow monitoring system consists of:

 * sFlow Agents that reside in network equipment which gather network traffic and port counters and combines the flow samples and interface counters into sFlow datagrams and forwards them to the sFlow collector at regular intervals over a UDP socket. The datagrams consist of information on, but not limited to, packet header, ingress and egress interfaces, sampling parameters, and interface counters. A single sFlow datagram may contain samples from many flows.
 * sFlow collectors which receive and analyze the sFlow data.

 sFlow is an industry standard, low cost and scalable technique that enables a single analyzer to provide a network wide view.

## 5. Requirements

sFlow will be implemented in multiple phases:

### **Phase I:**

1. sFlow should be supported on physical interfaces.
2. sFlow should support 2 sFlow collectors.
3. sFlow collector IP can be either IPv4 or IPv6.
4. sFlow collector can be reachable via
	1. 	Front end port
	2. 	Management port
5. Set the default sampling rate to 0, configuring non-default value should enable sFlow and start sampling.
6. Default sFlow sample size should be set to 128 bytes.
7. Support sFlow related
	1. CLI show/config commands
	2. syslogs


### **Phase II:**
1. sFlow should be supported on portchannel interfaces.
2. SNMP support for sFlow.
3. sFlow counter support needed.
4. Polling interval for sFlow counter.

### **Phase III:**
1. sFlow extended switch support.
2. sFlow extended router support.

### Not planned to be supported:
1. sFlow enable/disable option interface level as well as global level.
2. sFlow configuration at interface level.
3. Egress sampling support.
4. sFlow backoff mechanism (Drop the packets beyond configured CPU Queue rate limit).
5. sFlow over vlan interfaces.

## 6. Module Design

### 6.1 **Overall design**
The following figure depicts the sFlow container in relation to the overall SONiC architecture:

![alt text](../../images/sflow/sflow_architecture.png "SONiC sFlow Architecture")

The CLI is enhanced to provide configuring and display of sFlow parameters including sflow collectors, agent IP, sampling rate for interfaces. The CLI configurations currently only interact with the CONFIG_DB.

The newly introduced sflow container consists of:
* An instantiation of the InMon's hsflowd daemon (https://github.com/sflow/host-sflow described in https://sflow.net/documentation.php). The hsflowd is launched as a systemctl service. The host-sflow is customised to interact with SONiC subsystems by introducing a host-sflow/src/Linux/mod_sonic.c (descripted later)
* sflowmgrd : which is a python script that consumes sflow configurations from the CONFIG DB and:
       * configure the genetlink family and multicast group for sflow use
       * updates the hsflowd.conf

The swss container is enhanced to add the following component:
* sfloworch : which subscribes to the APP DB and acts as southbound interface to SAI for programming the SAI_SAMPLEPACKET sessions, genetlink channel, multicast group and sampling parameters.

The syncd container is enhanced to support the SAI SAMPLEPACKET APIs.

The ASIC drivers need to be enhanced to:
* Associate the SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET to a specific genetlink channel and group.
* Punt trapped samples to this genetlink group

The sflow container and changes to the existing components to support sflow are described in the following sections.

### 6.2 **Configuration and control flow**
The following figure shows the configuration and control flows for sFlow:

![alt text](../../images/sflow/sflow_config_and_control.png "SONiC sFlow Configuration and Control")

1. The user configures the sflow collector, agent, sampling related parameters (rate), genetlink parameters (genetlink family and multicast group) and these configurations are added to the CONFIG DB.
2. The sflowmgrd watches the configDB's SFLOW_GENETLINK table and creates a genetlink family and multicast group. This will eventually be  used by the ASIC SAI driver to punt sFlow samples to hsflowd. Once the genetlink group is created, the sflowmgrd initializes the SFLOW_GENETLINK_TABLE in the APP Db that contains the trap type (SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET) and the genetlink channel and group.
3. The sfloworch processes the SFLOW_GENETLINK_TABLE changes and calls a SAI API that enables the ASIC driver to map the SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET trap to the specific genetlink channel and group.
4. The sflowmgrd daemon watches the CONFIG DB's SFLOW_COLLECTOR table and updates the /etc/hsflowd.conf which is the configuration file for hsflowd. Based on the nature of changes, the sflowmgrd may restart the hsflowd service. The hsflowd service uses the collector, UDP port and agent IP information to open sockets to reach the sFlow collectors.
5. When hsflowd starts, the sonic module (mod_sonic) registered callback for packetBus/HSPEVENT_CONFIG_CHANGED opens a netlink socket for packet reception and registers an sflow sample handler over the netlink socket (HsflowdRx()).
6. Sampling rate changes are updated in the SFLOW table. The sflowmgrd updates sampling rate changes into SFLOW_TABLE in the App DB. The sfloworch subagent in the orchagent container processes the change to propagate as corresponding SAI SAMPLEPACKET APIs.


### 6.3 **sFlow sample path**
The following figure shows the sFlow sample packet path flow:

![alt text](../../images/sflow/sflow_sample_packet_flow.png "SONiC sFlow sample packet flow")

1. The ASIC (DMAs) an sflow sample and interrupts the ASIC driver
2. The ASIC driver ascertains that this is sample buffer that has been received as a result of sflow sampling being enabled for this interface.
3. The ASIC driver checks that SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKETs are associated with a specific genetlink channel name and group. the ASIC driver encapsulates the sample in a genetlink buffer and adds the following netlink attributes to the sample : IIFINDEX, OIFINDEX, ORIGSIZE, SAMPLE, SAMPLE RATE. The genetlink buffer is sent via genlmsg_multicast().
4. The hsflowd daemon's HsflowdRx() is waiting on the specific genetlink family name's multicast group id and receives the encapsulated sample. The HsflowdRx parses and extracts the encapsulated sflow attributes and injects the sample to the hsflowd packet thread using takeSample().
5. The hsflowd packet thread accumulates sufficient samples and then constructs an sFlow UDP datagram and forwards to the configured sFlow collectors.

### 6.4 **CLI**

#### sFlow utility interface
* sflow [options] {config | show} ...
  
  An sflow utility command is provided to operate with sflow configuration
  Also, the **config** and **show** commands would be extended to include the sflow option.

#### Config commands
* sflow collector \<add|del> \<name> <ipv4-address | ipv6-address> [agent-addr {ipv4-address | ipv6-address}] [port \<number>] [max-datagram-size \<size>]

  Where:
  * name is the unique name of the sFlow collector
  * ipv4-address : IP address of the collector in dotted decimal format for IPv4
  * ipv6-address : x: x: x: x::x format for IPv6 address of the collector (where :: notation specifies successive hexadecimal fields of zeros)
  * agent-addr : 
       * ipv4-address : IP address of the agent in dotted decimal format for IPv4
       * ipv6-address :  x: x: x: x::x format for IPv6 address of the agent (where :: notation specifies successive hexadecimal fields of zeros)
  * port : specifies the UDP port of the collector (the range is from 0 to 65535. The default is 6343.)
  * max-datagram-size : in bytes (from 400 to 1500 : defaults to 1400)

  Note:
  * A maximum of 2 collectors is allowed.
  * Only a single agent IP is allowed across collectors
  * Only a single value for max-datagram-size is allowed across collectors

 * no sflow collector \<name>

    Delete the sflow collector with the given name
 
* sflow sample-rate value
  
  Where
  * value is the average number of packets skipped before the sample is taken. As per SAI samplepacket definition : *"The sampling rate specifies random sampling probability as the ratio of packets observed to samples generated. For example a sampling rate of 100 specifies that, on average, 1 sample will be generated for every 100 packets observed."*
  * The value of 0 is used to disable sFlow.

* sflow genetlink \<add|del> \<name> \<multicast-group-id>

  Where
  * name is the Generic Netlink family name (defaults to psample)
  * multicast-group-id is the GENETLINK multicast group ID/port that will be used by hsflowd to receive the sFlow samples (default 100)

#### Show commands
* show sflow 
  * Displays the current configuration. Includes global defaults as well as user configured values including collectors.
* show runningconfiguration sflow
  * Displays the current running configuration of sflow

### 6.5 **DB and Schema changes**

#### ConfigDB Table & Schema

A new SFLOW_GENETLINK ConfigDB table entry would be added:
```
; Defines schema for SFLOW_GENETLINK table which has the genetlink family and multicast group IDs to be used as Host Interfaces
key                                   = SFLOW_GENETLINK:genetlink_name
; field                               = value
genetlink_name                        = 1*16VCHAR                        ; name of the genetlink family
genetlink_group                       = 1*4DIGIT                         ; genetlink multicast group id
```

A new SFLOW_COLLECTOR ConfigDB table entry would be added. 
```
SFLOW_COLLECTOR|{{collector_name}}
    "collector_ip": {{ip_address}}
    "agent_addr": {{ip_address}}
    "collector_port": {{ uint32 }} (OPTIONAL)
    "max_datagram_size": {{ uint32 }} (OPTIONAL)

; Defines schema for sFlow collector configuration attributes
key                                   = SFLOW_COLLECTOR:collector_name   ; sFlow collector configuration
; field                               = value
collector_ip                          = IPv4address / IPv6address        ; Ipv4 or IpV6 collector address
agent_ip                              = IPv4address / IPv6address        ; Ipv4 or IpV6 agent address
collector_port                        = 1*5DIGIT                         ; destination L4 port : a number between 0 and 65535
max_datagram_size                     = 1*4DIGIT                         ; MTU of the sflow datagram

;value annotations
collector_name                        = 1*16VCHAR
```

A new SFLOW table would be added.
```
; Defines schema for SFLOW table which holds global configurations
key                                   = SFLOW:Config
; field                               = value
sampling_rate       = 1*5DIGIT      ; 1 / (sflow sampling rate as a percentage of bandwidth)
```

#### AppDB & Schema

A new SFLOW_GENETLINK_TABLE table entry would be added:

```
; Defines schema for SFLOW_GENETLINK_TABLE table which maps trap types that need to be punted to a genetlink channel
key                                   = SFLOW_GENETLINK_TABLE:trap_id             ; TRAP ID
; field                               = value
genetlink_name                        = 1*16VCHAR                          ; name of the genetlink family
genetlink_group                       = 1*4DIGIT                           ; genetlink multicast group id
```

A new SFLOW_TABLE is added to the AppDB:

```
; Defines schema for SFLOW_TABLE table which contains parameters that need to be set for sFlow
key                 = SFLOW_TABLE:sflow
; field             = value
sampling_rate       = 1*5DIGIT           ; 1 / (sflow sampling rate as a percentage of bandwidth)
```

#### StateDB & Schema

The following SFLOW_STATE table is added to the StateDB:
```
; Defines schema for SFLOW_STATE table
; field                               = value
genetlink_state                       = "" / "initialized"               ; initialized : genetlink group created successfully
genetlink_trap                        = "" / "initialized"               ; initialized : trap has been mapped to genetlink group successfully
hsflowd_state                         = "" / "started" / "stopped" / "listening" ; started : hsflowd daemon has been started
                                                                                 ; stopped : hsflowd daemon has been stopped
                                                                                 ; listening : hsflowd is listening for samples
```

### 6.6 **sflow container**

hsflowd (https://github.com/sflow/host-sflow) is the most popular open source implementation of the sFlow agent and provides support for DNS-SD (http://www.dns-sd.org/) and can be dockerised. hsflowd supports sFlow version 5 (https://sflow.org/sflow_version_5.txt which supersedes RFC 3176). hsflowd will run as a systemd service within the sflow docker.

CLI configurations will be saved to the ConfigDB. Once the genetlink channel has been initialised and the sFlow traps mapped to the genetlink group, the hsflowd service is started. The service startup script will derive the /etc/hsflowd.conf from the ConfigDB. Config changes will necessitate restart of hsflowd. hsflowd provides the necessary statistics for the "show" commands. CLI "config" commands will retrieve the entries in the config DB.

#### sflowmgrd

The sflowmgrd reads the SFLOW_GENETLINK table to create program genetlink groups that will be used by the SAI driver to lift packets to the hsflowd. Once the genetlink group is created, updates the SFLOW_GENETLINK_TABLE table for sFlowOrch to process. A multicast group is typically created which enables multiple applications (e.g. even a local netlink sniffer tools) to additionally inspect the samples that are lifted to hsflowd.

the sflowmgrd daemon listens to SFLOW_COLLECTOR to construct the hsflowd.conf and start the hsflowd service.
The mapping between the SONiC sflow CLI parameters and the host-sflow is given below:

SONIC CLI parameter| hsflowd.conf equivalent
-------------------|------------------------
collector ip-address | collector.ip
collector port| collector.UDPPort
agent ip-address | agentIP
max-datagram-size | datagramBytes
sample-rate | sampling

The master list of supported host-sflow tokens are found in host-sflow/src/Linux/hsflowtokens.h

Example SONiC CLI configuration:

&#35; sflow collector add sflow-a 10.100.12.13 agent-addr 10.0.0.10 max-datagramsize 1500

&#35; sflow collector add sflow-b 10.144.1.2 pot 6344

&#35; sflow sample-rate 32768

```
sflow {
  agentIP = 10.0.0.10
  sampling = 32748
  collector { ip = 10.100.12.13 }
  collector { ip = 10.144.1.2 UDPPort=6344 }
  datagramBytes = 1500
}
```

sflowmgrd also listens to SFLOW to propogate the sampling rate changes to App DB SFLOW_TABLE.

#### hsflowd service

hsflowd provides an module adaptation layer for interfacing with the NOS. In the host-sflow repo, a src/Linux/mod_sonic.c adaption layer will be provided for hsflowd APIs to SONiC that deal with hsflowd initialization, configuration changes, packet sample consumption etc. More specifically, SONiC will register and provide callbacks for the following HSP events:

hsflowd bus/events|SONiC callback actions
------------------|----------------------
  pollBus/HSPEVENT_INTF_READ | select all switchports for sampling by default
  pollBus/HSPEVENT_INTF_SPEED | set sampling rate
  pollBus/HSPEVENT_UPDATE_NIO | poll interface state from STATE_DB:PORT_TABLE
  pollBus/HSPEVENT_CONFIG_CHANGED)| Change sampling rate (/ port speed changed)
  packetBus/HSPEVENT_CONFIG_CHANGED | open netlink socket and register HsflowdRx()
  
Refer to host-sflow/src/Linux/hsflowd.h for a list of events.

### 6.7 **SWSS and syncd changes**

### sFlowOrch

An sFlowOrch is introduced in the Orchagent to handle configuration requests. The sFlowOrch essentially facilitates the creation/deletion of samplepacket sessions as well as get/set of session specific attributes. sFlowOrch tracks the SFLOW_GENETLINK_TABLE table to set the genetlink host interface that is to be used by the SAI driver to deliver the samples.

Also, it monitors the SFLOW_TABLE and PORT state to determine sampling rate / speed changes to derive and set the sampling rate for all the interfaces. It uses the SAI samplepacket APIs to set each ports's sampling rate.

### 6.8 **SAI changes**

Creating sFlow sessions and setting attributes (e.g. sampling rate) is described in SAI proposal : https://github.com/opencomputeproject/SAI/tree/master/doc/Samplepacket 

As per the sFlow specification, each packet sample should have certain minimal meta data for processing by the sFlow analyser. The psample infrastructure (http://man7.org/linux/man-pages/man8/tc-sample.8.html) already describes the desired metadata fields (which the SAI driver needs to add to each sample):

```
SAMPLED PACKETS METADATA FIELDS
       The metadata are delivered to userspace applications using the
       psample generic netlink channel, where each sample includes the
       following netlink attributes:

       PSAMPLE_ATTR_IIFINDEX
              The input interface index of the packet, if there is one.

       PSAMPLE_ATTR_OIFINDEX
              The output interface index of the packet. This field is not
              relevant on ingress sampling

       PSAMPLE_ATTR_ORIGSIZE
              The size of the original packet (before truncation)

       PSAMPLE_ATTR_SAMPLE_GROUP
              The psample group the packet was sent to

       PSAMPLE_ATTR_GROUP_SEQ
              A sequence number of the sampled packet. This number is
              incremented with each sampled packet of the current psample
              group

       PSAMPLE_ATTR_SAMPLE_RATE
              The rate the packet was sampled with
```

The SAI driver may provide the interface OIDs corresponding to the IIFINDEX AND OIFINDEX. The hsflowd mod_sonic HsflowdRx() may have to map these correspondingly to the netdev ifindex.

Rather than define a new framework for describing the metadata for sFlow use, SAI would re-use the framework that the psample driver (https://github.com/torvalds/linux/blob/master/net/psample/psample.c) currently uses. The psample kernel driver is based on the Generic Netlink subsystem that is described in https://wiki.linuxfoundation.org/networking/generic_netlink_howto. SAI ASIC drivers supporting sFlow may choose to use the psample.ko driver as-is or may choose to implement the generic netlink interface (that complies with the above listed metadata) using a private generic netlink family.

#### SAI Host Interface based on Generic Netlink

1. Application installs psample.ko (genl family = "psample") or it's own psample metadata compliant kernel driver (say, genl family ="asic_genl")

2. Application creates a multicast group in the generic netlink family for use by SAI driver to lift samples on the chosen genetlink family’s multicast port.

3. Use sai_create_hostif_fn() to let SAI driver know of SAI_HOST_INTERFACE_TYPE_GENETLINK interface associated with generic netlink family (SAI_HOST_INTERFACE_ATTR_NAME) and mulsticast group id (SAI_HOSTIF_ATTR_GENETLINK_PORT_ID)

4. Use sai_create_hostif_table_entry_fn() to map SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET to sai_host_if

#### Changes in SAI to support the GENETLINK host interface

The changes in SAI to support the GENETLINK host interface is highlighted below:

```
 /** Generic netlink */
    SAI_HOSTIF_TYPE_GENETLINK

 /**
     * @brief Name [char[SAI_HOSTIF_NAME_SIZE]]
     *
     * The maximum number of characters for the name is SAI_HOSTIF_NAME_SIZE - 1 since
     * it needs the terminating null byte ('\0') at the end.
     *
     * In case of GENETLINK, name refers to the genl family name
     *
     * @type char
     * @flags MANDATORY_ON_CREATE | CREATE_ONLY
     * @condition SAI_HOSTIF_ATTR_TYPE == SAI_HOSTIF_TYPE_NETDEV or SAI_HOSTIF_ATTR_TYPE == SAI_HOSTIF_TYPE_GENETLINK
     */
    SAI_HOSTIF_ATTR_NAME,

 /**
     * @brief Set the Generic netlink (multicast) port id on which the packets/buffers
     * are received on this host interface
     *
     * @type sai_uint32_t
     * @flags CREATE_AND_SET
     * @default 0
     */
    SAI_HOSTIF_ATTR_GENETLINK_PORT_ID,

 /** Receive packets via Linux generic netlink interface */
    SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK
```
#### Creating a GENETLINK Host Interface

Below is an example code snip that shows how a GENETLINK based host inerface is created. It is assumed that the application has already installed the psample.ko and created multicast group 100.

```
// Create a Host Interface based on generic netlink
sai_object_id_t host_if_id;
sai_attribute_t sai_host_if_attr[3];
 
sai_host_if_attr[0].id=SAI_HOST_INTERFACE_ATTR_TYPE;
sai_host_if_attr[0].value=SAI_HOST_INTERFACE_TYPE_GENETLINK;
 
sai_host_if_attr[1].id= SAI_HOST_INTERFACE_ATTR_NAME;
sai_host_if_attr[1].value=”psample”;
 
sai_host_if_attr[2].id= SAI_HOSTIF_ATTR_GENETLINK_PORT_ID;
sai_host_if_attr[2].value=100;

sai_create_host_interface_fn(&host_if_id, 9, sai_host_if_attr);
```

### Mapping a sFlow (SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET) trap to a GENETLINK host interface multicast group id

Below is the code snip that outlines how an sFlow trap is mapped to the GENETLINK host interface created in the previous section.

```
// Configure the host table to receive traps on the generic netlink socket

sai_object_id_t host_table_entry;
sai_attribute_t sai_host_table_attr[9];
 
sai_host_table_attr[0].id=SAI_HOSTIF_TABLE_ENTRY_ATTR_TYPE;
sai_host_table_attr[0].value= SAI_HOST_INTERFACE_TABLE_ENTRY_TYPE_TRAP_ID;
 
sai_host_table_attr[1].id= SAI_HOSTIF_TABLE_ENTRY_ATTR_TRAP_ID;
sai_host_table_attr[1].value=sflow_trap_id; // Object referencing SAMPLEPACKET trap

sai_host_table_attr[2].id= SAI_HOSTIF_TABLE_ENTRY_ATTR_CHANNEL;
sai_host_table_attr[2].value=  SAI_HOSTIF_TABLE_ENTRY_CHANNEL_TYPE_GENETLINK; 

sai_host_table_attr[3].id= SAI_HOSTIF_TABLE_ENTRY_ATTR_HOST_IF;
sai_host_table_attr[3].value=host_if_id; // host interface of type file descriptor for GENETLINK

sai_create_hostif_table_entry_fn(&host_table_entry, 4, sai_host_table_attr);
```

It is assumed that the trap group and the trap itself have been defined using sai_create_hostif_trap_group_fn() and sai_create_hostif_trap_fn().

## 7 **sFlow in Virtual Switch**

On the SONiC VS, SAI calls would map to the tc_sample commands on the switchport interfaces (http://man7.org/linux/man-pages/man8/tc-sample.8.html).

## 8 **Build**

* The host-sflow package will be built with the mod_sonic callback implementations using the FEATURES="SONIC" option

## 9 **Restrictions**
* /etc/hsflowd.conf should not be modified manually. While it should be possible to change /etc/hsflowd.conf manually and restart the sflow container, it is not recommended.
* Management VRF support: TBD
* configuration updates will necessitate hsflowd service restart

## 10 **Action items**
* Unit Test cases