# sFlow High Level Design
### Rev 0.4
## Table of Contents

## 1. Revision 
Rev | Rev	Date	| Author	| Change Description
---------|--------------|-----------|-------------------
v0.1 |05/01/2019  |Padmanabhan Narayanan | Initial version
v0.2 |05/20/2019  |Padmanabhan Narayanan | Updated based on internal review comments
v0.3 |06/11/2019  |Padmanabhan Narayanan | Update CLIs, remove sflowcfgd 
v0.4 |06/17/2019  |Padmanabhan Narayanan | Add per-interface configurations, counter mode support and <br /> unit test cases. Remove genetlink CLI

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
8. sFlow counter support needed.

### **Phase II:**
1. sFlow should be supported on portchannel interfaces.
2. Enhance CLI with session support (i.e create sessions add interfaces to specific sessions)
3. SNMP support for sFlow.
4. Polling interval for sFlow counter.

### **Phase III:**
1. sFlow extended switch support.
2. sFlow extended router support.

### Not planned to be supported:
1. Egress sampling support.
2. sFlow backoff mechanism (Drop the packets beyond configured CPU Queue rate limit).
3. sFlow over vlan interfaces.

## 6. Module Design

### 6.1 **Overall design**
The following figure depicts the sFlow container in relation to the overall SONiC architecture:

![alt text](../../images/sflow/sflow_architecture.png "SONiC sFlow Architecture")

The CLI is enhanced to provide configuring and display of sFlow parameters including sflow collectors, agent IP, sampling rate for interfaces. The CLI configurations currently only interact with the CONFIG_DB.

The newly introduced sflow container consists of:
* An instantiation of the InMon's hsflowd daemon (https://github.com/sflow/host-sflow described in https://sflow.net/documentation.php). The hsflowd is launched as a systemctl service. The host-sflow is customised to interact with SONiC subsystems by introducing a host-sflow/src/Linux/mod_sonic.c (descripted later)
* sflowmgrd : 
       * configure the genetlink family and multicast group for sflow use if necessary
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

1. The user configures the sflow collector, agent, sampling related parameters (interfaces to be sampled and rate) and these configurations are added to the CONFIG DB.
2. The sflowmgrd checks if the genetlink family "psample" and multicast group for sflow samples exists and if not, creates a genetlink family and multicast group. This will eventually be  used by the ASIC SAI driver to punt sFlow samples to hsflowd.
3. The sfloworch calls a SAI API that enables the ASIC driver to map the SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET trap to the specific genetlink channel and group.
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

### 6.4 **sFlow counters**

The sFlow counter polling interval is set to 20 seconds. The pollBus/HSPEVENT_UPDATE_NIO callback caches the interface SAI OIDs during the first call by querying COUNTER_DB:COUNTERS_PORT_NAME_MAP. It periodically retrieves the COUNTER_DB interface counters and fills the necessary counters in hsflowd's SFLHost_nio_counters.

### 6.5 **CLI**

#### sFlow utility interface
* sflow [options] {config | show} ...
  
  An sflow utility command is provided to operate with sflow configuration
  Also, the **config** and **show** commands would be extended to include the sflow option.

#### Config commands

* **sflow collector add** *{collector-name {ipv4-address | ipv6-address}}* **agent-addr** *{ipv4-address | ipv6-address} [**port** {number}] [**max-datagram-size** {size}]*

  Where:
  * name is the unique name of the sFlow collector
  * ipv4-address : IP address of the collector in dotted decimal format for IPv4
  * ipv6-address : x: x: x: x::x format for IPv6 address of the collector (where :: notation specifies successive hexadecimal fields of zeros)
  * agent-addr : 
    * ipv4-address : IP address of the agent in dotted decimal format for IPv4
    * ipv6-address : x: x: x: x::x format for IPv6 address of the agent (where :: notation specifies successive hexadecimal fields of zeros)
  * port (OPTIONAL): specifies the UDP port of the collector (the range is from 0 to 65535. The default is 6343.)
  * max-datagram-size (OPTIONAL): in bytes (from 400 to 1500 : defaults to 1400)

  Note:
  * A maximum of 2 collectors is allowed.
  * Only a single agent IP is allowed across collectors
  * Only a single value for max-datagram-size is allowed across collectors

 * **sflow collector del** *{collector-name}*

    Delete the sflow collector with the given name
 
* **sflow sample-rate** *value*
  
   Configure the global default sample-rate
    
   * value is the average number of packets skipped before the sample is taken. As per SAI samplepacket definition : "The sampling rate specifies random sampling probability as the ratio of packets observed to samples generated. For example a sampling rate of 100 specifies that, on average, 1 sample will be generated for every 100 packets observed."
   * Valid range 256:8388608. Global default sample-rate is 32768
   * When this value is changed, only interfaces that are subsequently configured for sampling inherit this value.

* **sflow interface <enable|disable>** *{interface-name}*

   Enable/disable sflow on an interface

* **sflow interface sample-rate** *{interface-name} {value}*

  Enable sample-rate for the specific interface : this value overrides the global default setting. Valid range 256:8388608.

#### Show commands

* **show sflow**
  * Displays the current configuration, global defaults as well as user configured values including collectors.
* **show sflow interface**
  * Displays the current running configuration of sflow interfaces.

#### Example SONiC CLI configuration ####

&#35; sflow collector add sflow-a 10.100.12.13 agent-addr 10.0.0.10 max-datagramsize 1500

&#35; sflow collector add sflow-b 10.144.1.2 pot 6344

&#35; sflow interface enable Ethernet0

&#35; sflow interface enable Ethernet16

&#35; sflow interface sample-rate Ethernet16 65536

The configDB objects for the above CLI is given below:

```
{
    "SFLOW_COLLECTOR": {
        "collector1": {
            "collector_ip": "10.100.12.13",
            "agent_addr": "10.0.0.10",
            "collector_port": "6343"
            "max_datagram_size": "1500"
        },
        "collector2": {
            "collector_ip": "10.144.1.2",
            "agent_addr": "10.0.0.10",
            "collector_port": "6344"
            "max_datagram_size": "1400"
        }
    },

    "SFLOW_SESSION": {
        "global": {
           "admin_state": "enable"
           "sample_rate": "32768"
        },
        "global|Ethernet0": {
           "admin_state": "enable"
           "sample_rate": "32768"
        }
        "global|Ethernet16": {
           "admin_state": "enable"
           "sample_rate": "65536"
        }
    }

```

&#35; show sflow 
```
sFlow services are enabled
Global default sampling rate: 32768
Global default counter polling interval: 20
Global default extended maximum header size: 128 bytes
2 collectors configured:
Collector IP addr: 10.100.12.13, Agent IP addr: 10.0.0.10, UDP port: 6343 max datagram size 1500
Collector IP addr: 10.144.1.2, Agent IP addr: 10.0.0.10, UDP port: 6344 max datagram size 1400
```

&#35; show sflow interface

```
Interface     Admin Status   Sampling rate 
---------     ------------   -------------
Ethernet0     Enabled        32768

Ethernet16    Enabled        65536
```

### 6.6 **DB and Schema changes**

#### ConfigDB Table & Schema

A new SFLOW_COLLECTOR ConfigDB table entry would be added. 
```
SFLOW_COLLECTOR|{{collector_name}}
    "collector_ip": {{ip_address}}
    "agent_addr": {{ip_address}}
    "collector_port": {{ uint32 }} (OPTIONAL)
    "max_datagram_size": {{ uint32 }} (OPTIONAL)

; Defines schema for sFlow collector configuration attributes
key                         = SFLOW_COLLECTOR:collector_name   ; sFlow collector configuration
; field                     = value
COLLECTOR_IP                = IPv4address / IPv6address  ; Ipv4 or IpV6 collector address
AGENT_IP                    = IPv4address / IPv6address  ; Ipv4 or IpV6 agent address
COLLECTOR_PORT              = 1*5DIGIT      ; destination L4 port : a number between 0 and 65535
MAX_DATAGRAM_SIZE           = 1*4DIGIT      ; MTU of the sflow datagram

;value annotations
collector_name              = 1*16VCHAR
```

A new SFLOW_SESSION table would be added.
```
SFLOW_SESSION|{{session_name}}
    "admin_state": "enable" / "disable"
    "sample_rate": 1*7DIGIT   ; average number of packets skipped before the sample is taken

SFLOW_SESSION|{{session_name}}|{{interface_name}}
    "admin_state": "enable" / "disable"
    "sample_rate": 1*7DIGIT   ; average number of packets skipped before the sample is taken

; Defines schema for SFLOW_SESSION table which holds global configurations
key 			= SFLOW_SESSION:session_name
ADMIN_STATE	    	= "enable" / "disable"
SAMPLE_RATE 		= 1*7DIGIT      ; average number of packets skipped before the sample is taken

key                     = SFLOW_SESSION:session_name:interface_name
ADMIN_STATE		= "enable" / "disable"
SAMPLE_RATE 		= 1*7DIGIT   ; average number of packets skipped before the sample is taken
```

In Phase I, the default session would be "global".

#### AppDB & Schema

A new SFLOW_SESSION_TABLE is added to the AppDB:

```
; Defines schema for SFLOW_SESSION_TABLE which holds global configurations
key 			= SFLOW_SESSION_TABLE:session_name
ADMIN_STATE	    	= "enable" / "disable"
SAMPLE_RATE 		= 1*7DIGIT      ; average number of packets skipped before the sample is taken

key                     = SFLOW_SESSION_TABLE:session_name:interface_name
ADMIN_STATE		= "enable" / "disable"
SAMPLE_RATE 		= 1*7DIGIT   ; average number of packets skipped before the sample is taken
```

### 6.7 **sflow container**

hsflowd (https://github.com/sflow/host-sflow) is the most popular open source implementation of the sFlow agent and provides support for DNS-SD (http://www.dns-sd.org/) and can be dockerised. hsflowd supports sFlow version 5 (https://sflow.org/sflow_version_5.txt which supersedes RFC 3176). hsflowd will run as a systemd service within the sflow docker.

CLI configurations will be saved to the ConfigDB. Once the genetlink channel has been initialised and the sFlow traps mapped to the genetlink group, the hsflowd service is started. The service startup script will derive the /etc/hsflowd.conf from the ConfigDB. Config changes will necessitate restart of hsflowd. hsflowd provides the necessary statistics for the "show" commands. CLI "config" commands will retrieve the entries in the config DB.

#### sflowmgrd

The sflowmgrd queries if the genetlink family "psample" and the multicast groun #270 exists and if not creates it so that that will be used by the SAI driver to lift packets to the hsflowd. A multicast group is typically created which enables multiple applications (e.g. even a local netlink sniffer tools) to additionally inspect the samples that are lifted to hsflowd.

The sflowmgrd daemon listens to SFLOW_COLLECTOR to construct the hsflowd.conf and start the hsflowd service.
The mapping between the SONiC sflow CLI parameters and the host-sflow is given below:

SONIC CLI parameter| hsflowd.conf equivalent
-------------------|------------------------
collector ip-address | collector.ip
collector port| collector.UDPPort
agent ip-address | agentIP
max-datagram-size | datagramBytes
sample-rate | sampling

The master list of supported host-sflow tokens are found in host-sflow/src/Linux/hsflowtokens.h

sflowmgrd also listens to SFLOW to propogate the sampling rate changes to App DB SFLOW_TABLE.

#### hsflowd service

hsflowd provides an module adaptation layer for interfacing with the NOS. In the host-sflow repo, a src/Linux/mod_sonic.c adaption layer will be provided for hsflowd APIs to SONiC that deal with hsflowd initialization, configuration changes, packet sample consumption etc. More specifically, SONiC will register and provide callbacks for the following HSP events:

hsflowd bus/events|SONiC callback actions
------------------|----------------------
  pollBus/HSPEVENT_INTF_READ | select all switchports for sampling by default
  pollBus/HSPEVENT_INTF_SPEED | set sampling rate
  pollBus/HSPEVENT_UPDATE_NIO | poll interface state from STATE_DB:PORT_TABLE and update counter stats in SFLHost_nio_counters from COUNTER DB
  pollBus/HSPEVENT_CONFIG_CHANGED)| Change sampling rate (/ port speed changed)
  packetBus/HSPEVENT_CONFIG_CHANGED | open netlink socket and register HsflowdRx()
  
Refer to host-sflow/src/Linux/hsflowd.h for a list of events.

### 6.8 **SWSS and syncd changes**

### sFlowOrch

An sFlowOrch is introduced in the Orchagent to handle configuration requests. The sFlowOrch essentially facilitates the creation/deletion of samplepacket sessions as well as get/set of session specific attributes. sFlowOrch sets the genetlink host interface that is to be used by the SAI driver to deliver the samples.

Also, it monitors the SFLOW_SESSIONS_TABLE and PORT state to determine sampling rate / speed changes to derive and set the sampling rate for all the interfaces. It uses the SAI samplepacket APIs to set each ports's sampling rate.

### Rate limiting

Considering that sFlow backoff mechanism is not being implemented, users should consider rate limiting sFlow samples using the currently existing COPP mechanism (the COPP config (e.g. src/sonic-swss/swssconfig/sample/00-copp.config.json) can include appropriate settings for the samplepacket trap and initialised using swssconfig).

### 6.9 **SAI changes**

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

## 7 **Warmboot support**

sFlow packet/counter sampling should not be affected after a warm reboot. In case of a planned warm reboot, packet sampling will be stopped.

## 8 **sFlow in Virtual Switch**

On the SONiC VS, SAI calls would map to the tc_sample commands on the switchport interfaces (http://man7.org/linux/man-pages/man8/tc-sample.8.html).

## 9 **Build**

* The host-sflow package will be built with the mod_sonic callback implementations using the FEATURES="SONIC" option

## 10 **Restrictions**
* /etc/hsflowd.conf should not be modified manually. While it should be possible to change /etc/hsflowd.conf manually and restart the sflow container, it is not recommended.
* Management VRF support: TBD
* configuration updates will necessitate hsflowd service restart

## 11 **Unit Test cases**
Unit test case one-liners are given below:
 S.No| Test case synopsis
-----|-------------------
1|Verify that the SFLOW_COLLECTOR configuration additions from CONFIG_DB are processed by hsflowd.
2|Verify that the SFLOW_COLLECTOR configuration deletions from CONFIG_DB are processed by hsflowd.
3|Verify that sFlowOrch creates "psample" multicast group 270 if there is not psample driver inserted.
4|Verify that sFlowOrch maps SAI_HOSTIF_TRAP_TYPE_SAMPLEPACKET trap to the "psample" family and multicast group 270.
5|Verify that it is possible to enable and disable sflow using the SFLOW_SESSION global admin_state field in CONFIG_DB
6|Verify that interfaces can be enabled/disabled using additions/deletions in SFLOW_SESSION table in CONFIG_DB
7|Verify that it is possible to change the default global sampling rate using SFLOW_SESSION global sample_rate field in CONFIG_DB
8|Verify that it is possible to change the sampling rate per interface using SFLOW_SESSION interface sample_rate field in CONFIG_DB
9|Verify that changes to SFLOW_SESSION CONFIG_DB entry is pushed to the corresponding table in APP_DB and to ASIC_DB by sFlowOrch
10|Verify that collector and per-interface changes get reflected using the "show sflow" and "show sflow interface" commands
11|Verify that packet samples are coming into hsflowd agent as per the global and per-interface configuration
12|Verify that the hsflowd generated UDP datagrams are generated as expected and contain all the PSAMPLE_ATTR* attributes in the meta data.
13|Verify that samples are received when either 1 or 2 collectors are configured.
14|Verify the sample collection for both IPv4 and IPv6 collectors.
15|Verify that sample collection works on all ports or on a subset of ports (using lowest possible sampling rate).
16|Verify that counter samples are updated every 20 seconds
17|Verify that packet & counter samples stop for a disabled interface.
18|Verify that sampling changes based on interface speed and per-interface sampling rate change.
19|Verify that if sFlow is not enabled in the build, the sflow docker is not started
20|Verify that sFlow docker can be stopped and restarted and check that packet and counter sampling restarts.
21|Verify that with config saved in the config_db.json, restarting the unit should result in sFlow coming up with saved configuration.
22|Verify sFlow functionality with valid startup configuration and after a normal reboot, fast-boot and warm-boot.
23|Verify that the sFlow hsflowd logs are emitted to the syslog file for various severities.

## 12 **Action items**
* Determine if it is possible to change configuration without restarting hsflowd
* Check host-sflow licensing options