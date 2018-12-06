# Router interface counters in SONiC
### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definitions/Abbreviation](#definitionsabbreviation)

  * [1 Requirements](#1-overview)

  * [2 CLI format](#2-cli-format)

  * [3 Modules Design](#3-modules-design)
    * [3.1 Modules that need to be updated](#31-modules-that-need-to-be-updated)
      * [3.1.1 Counter DB](#311-counter-db)
      * [3.1.2 CLI](#312-cli)
      * [3.1.3 Orchestration Agent](#313-orchestration-agent)
      * [3.1.4 Flex Counter](#314-flex-counter)
      * [3.1.5 SAI](#318-sai)

  * [4 Open questions](#4-open-questions)

# List of Tables
* [Table 1: Revision](#revision)
* [Table 2: Abbreviations](#definitionsabbreviation)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Mykola Faryma      | Initial version                   |

# About this Manual
This document provides general information about RIF counter feature in SONiC.
# Scope
This document describes the high level design of the RIF counters.
# Definitions/Abbreviation
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| RIF                      | Router interface                           |
| FC                       | Flex counter                               |
| API                      | Application Programmable Interface         |
| SAI                      | Switch Abstraction Interface               |

# 1 Requirements

Add new CLI commands to show L3 interfaces counters. L3 interface counters refers to router port as well as vlan interface.
The information should be: RX: OK, ERR in packets and bytes. TX: OK, ERR in packets and bytes 
 
# 2 CLI format
The CLI command format and example output

```
$ show interfaces counters rif [OPTOINS] [interface_name]

 Show interface counters

Options:

  -p, --period TEXT

  --verbose          Enable verbose output

  -?, -h, --help     Show this message and exit.
```

Note: the 'show interfaces counters' has '-c, --clear' option. From the CLI point of view, this should be available from 'sonic-clear' CLI. (There already is 'sonic-clear interfaces counters')

If we would like to allign the options, I suggest to remove the clear option from the 'show interfaces counters'  command. 

The period option gives the ability to see the counters and RX/TX BPS, PPS and utilization rates.

The rates are calculated the following way:

BPS = (new_*_OCTETS - old_*_OCTETS) / delta,

Where delta is the period specified. The BPS is printed in MB/s, KB/s or B/s depending on the value.

PPS = (new_*_PACKETS - old_*_PACKETS) / delta

To clear the counters, the following CLI is available:

$ sonic-clear interface rifcounters [interface_name]

We will support both clearing the counters for a single RIF as well as all at once.

# Example output:

If the interface name is not provided, all the RIFs counters will be printed:

$ show interfaces counters rif
```
      IFACE       RX_OK    RX_BPS    RX_PPS    RX_ERR    TX_OK    TX_BPS    Tx_PPS    TX_ERR
-----------       -------  --------  ----------------  -------  --------  ---------  --------  
Ethernet0         2180       N/A       N/A        0       44697      N/A       N/A     0      
Ethernet4         47342      N/A       N/A        0       8362       N/A       N/A     0      
Ethernet8         2188       N/A       N/A        0       9379       N/A       N/A     0      
Ethernet12        46882      N/A       N/A        0       44448      N/A       N/A     0      
 ...
Portchannel0002   2833       N/A       N/A        0       0          N/A       N/A     0   
 ...
Vlan2             2833       N/A       N/A        0       4170       N/A       N/A     0
```

Providing a RIF name will print the counters in a more debug-friendly manner.

If the interface name does not exist in COUNTERS_RIF_NAME_MAP table, we'll output a warning message.

$ show interfaces counters rif Portchannel0002

```
Portchannel0002
---------------
  RX:
    0 packets           
    0 bytes             
    0 error packets     
    0 error bytes       

  TX:
    0 packets           
    0 bytes             
    0 error packets     
    0 error bytes       
```
# SAI counters definition:
```
  RX:
    packets           - SAI_ROUTER_INTERFACE_STAT_IN_PACKETS
    bytes             - SAI_ROUTER_INTERFACE_STAT_IN_OCTETS
    error packets     - SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS
    error bytes       - SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS

  TX:
    packets           - SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS
    bytes             - SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS
    error packets     - SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS
    error bytes       - SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS
```

# 3 Modules Design
## 3.1 Modules that need to be updated

### 3.1.1 Counter DB

#### The following new Queue counters should be available for each queue entry in the DB:
- "COUNTERS:rif_vid"
  - SAI_ROUTER_INTERFACE_STAT_IN_PACKETS
  - SAI_ROUTER_INTERFACE_STAT_IN_OCTETS
  - SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS
  - SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS
  - SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS
  - SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS
  - SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS
  - SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS

#### Additionally a few mappings should be added:
- "COUNTERS_RIF_TYPE_MAP" - map RIF to its type (e.g. LAG, Vlan)
- "COUNTERS_RIF_NAME_MAP" - map RIF oid to its name

### 3.1.2 CLI

Add new show interfaces counters subcommand, add rifstat script, try to reuse  portstat code.

### 3.1.3 SWSS

IntfsOrch should be updated:
 - Add/remove RIFs to Flex counter
 - implement the Counters Db maps generation

### 3.1.4 Flex counter

Add router interface stats support. Implement new FC group for RIFs.

Let's set the default FC interval to 1 second, same as for port counters.

### 3.1.5 SAI

The sai APIs and calls are:

sai_router_interface_api -> sai_get_router_interface_stats()

```
/**
 * @brief Router interface counter IDs in sai_get_router_interface_stats() call
 */
typedef enum _sai_router_interface_stat_t
{
    /** Ingress byte stat count */
    SAI_ROUTER_INTERFACE_STAT_IN_OCTETS,

    /** Ingress packet stat count */
    SAI_ROUTER_INTERFACE_STAT_IN_PACKETS,

    /** Egress byte stat count */
    SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS,

    /** Egress packet stat count */
    SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS,

    /** Byte stat count for packets having errors on router ingress */
    SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS,

    /** Packet stat count for packets having errors on router ingress */
    SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS,

    /** Byte stat count for packets having errors on router egress */
    SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS,

    /** Packet stat count for packets having errors on router egress */
    SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS

} sai_router_interface_stat_t;
```

### 3.1.5 SNMP

RIF counters can be exposed vie RFC1213 interface MIB.

They will differ from ports by the ifType and base index.

IANAifType:

| Value | Type |
| --- | ------ |
| 6 | ethernetCsmacd |
| 136 |	l3ipvlan |
| 161 | ieee8023adLag |
 
Base index : TBD

Currently defined base indexes: 

| Type | Base index |
| ---- | ---------- |
| ethernet | 1 |
| portchannel |	1000 |
| mgmt_port | 10000 |

Proposed SNMP OIDs to be used:

| OID | SNMP counter | Description | SAI stat | 
| --- | ------------ | ----------- | -------- |
| 1.3.6.1.2.1.2.2.1.10 | ifInOctets | The total number of octets received on the interface, including framing characters. | SAI_ROUTER_INTERFACE_STAT_IN_OCTETS |
| 1.3.6.1.2.1.2.2.1.11 | ifInUcastPkts | The number of packets, delivered by this sub-layer to a higher (sub-)layer, which were not addressed to a multicast or broadcast address at this sub-layer. | SAI_ROUTER_INTERFACE_STAT_IN_PACKETS |
| 1.3.6.1.2.1.2.2.1.14 | ifInErrors | For packet-oriented interfaces, the number of inbound packets that contained errors preventing them from being deliverable to a higher-layer protocol. | SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS |
| 1.3.6.1.2.1.2.2.1.16 | ifOutOctets | The total number of octets transmitted out of the interface, including framing characters. | SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS |
| 1.3.6.1.2.1.2.2.1.17 | ifOutUcastPkts | The total number of packets that higher-level protocols requested be transmitted, and which were not addressed to a multicast or broadcast address at this sub-layer, including those that were discarded or not sent. | SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS |
| 1.3.6.1.2.1.2.2.1.20 | ifOutErrors| For packet-oriented interfaces, the number of outbound packets that could not be transmitted because of errors. For character-oriented or fixed-length interfaces, the number of outbound transmission units that could not be transmitted because of errors. | SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS |

It looks like the SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS and SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS include bad packets, error and discard. The MIB has separate OIDs - ifInDiscards, ifInErrors, ifOutDiscards, ifOutErrors. Not sure how to handle this. 

### 4 Open questions

#### 4.1 What should be the base index (SNMP) for Vlan Interfaces?

#### 4.2 Allign the CLi options with 'show interfaces counters' --clear option. Remove existing clear option from the show command? 

#### 4.3 SNMP support and OIDs to be used.
