# Port illegal packets drop design

### High level design document

# List of Tables
* [Table 1: Revision](#revision)
* [Table 2: Abbreviations](#definitionsabbreviation)
* [Table 3: SAI counter mapping](#rfc1213-etries-and-sai-counter-mapping)
* [Table 4: IANA ifTypes](#interface-types-and-iana-iftypes)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Mykola Faryma      | Initial version                   |


### About this document

This document provides general information about the design of l3 drop packets via SNMP in SONiC.

### Scope

This document describes the high level design of Interface MIB extension (RFC1213) in regard to l3 counters.

###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| SNMP                     | Simple Network Management Protocol         |
| API                      | Application Programmable Interface         |
| SAI                      | Switch Abstraction Interface               |

# Requirements

The l3 interface counters should be accessible via SNMP Interface MIB.
For RIFs, the l3 counters are added to the l2 counters of the underlay port.

# Modules design

The l3 counters are polled to the COUNTERS_DB by the rifcounter flex counter groups. 
The RIF counters is not enabled/supported for every vendor (expected that l3 drops are counted in l2 drops for these platforms). 
The MIB should work regardsless of RIF FC group is enabled or not.

## RFC1213 entries and SAI counter mapping

Lets define a mapping for MIB entries to the SAI counters (l2 & l3):

| MIB entry          | L2 SAI counter | L3 SAI counter |
| ------------------ |:--------------:| :-------------:|
| ifInOctets         | SAI_PORT_STAT_IF_IN_OCTETS          | SAI_ROUTER_INTERFACE_STAT_IN_OCTETS  |
| ifInUcastPkts      | SAI_PORT_STAT_IF_IN_UCAST_PKTS      | SAI_ROUTER_INTERFACE_STAT_IN_PACKETS |
| ifInNUcastPkts     | SAI_PORT_STAT_IF_IN_NON_UCAST_PKTS  | |
| ifInDiscards       | SAI_PORT_STAT_IF_IN_DISCARDS        | |
| ifInErrors         | SAI_PORT_STAT_IF_IN_ERRORS          | SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS |
| ifInUnknownProtos  | SAI_PORT_STAT_IF_IN_UNKNOWN_PROTOS  | |
| ifOutOctets        | SAI_PORT_STAT_IF_OUT_OCTETS         | SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS |
| ifOutUcastPkts     | SAI_PORT_STAT_IF_OUT_UCAST_PKTS     | SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS |
| ifOutNUcastPkts    | SAI_PORT_STAT_IF_OUT_NON_UCAST_PKTS | |
| ifOutDiscards      | SAI_PORT_STAT_IF_OUT_DISCARDS       | |
| ifOutErrors        | SAI_PORT_STAT_IF_OUT_ERRORS         | SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS |
| ifOutQLen          | SAI_PORT_STAT_IF_OUT_QLEN           | |

## Interface  types and IANA iftypes

The `ifType` for each of the interfaces: 

| Interface  | IANA Iftype | Proposed implementation  |
| ---------- |:--------------:| :---------:|
| port       | 6 ethernetCsmacd       | Already implemented |
| RIF        | - | Add RIF counter values to port counters according to Table 3 |
| Vlan Int   | 136 l3ipvlan           | Implement new interface with type 136 |
| Lag        | 161 ieee8023adLag      | Already implemented |

## py-swsssdk changes

Extend py-swsssdk to provide utility functions to:
 - get oid mapping between RIFs and ports.
 - get vlan interface oid list

Example:
```
>>> port_util.get_rif_port_map(db)                                                                                                                                                                                                 
{'60000000007c7': '1000000000587' [, 'rif_oid': 'port_oid']}
```


## sonic-snmpagent changes

Interface MIB's `InterfacesUpdater` will contain port to rif map. When counters are updated if RIF oid is present in the "COUNTERS" table of COUNTERS_DB,
the counters are aggredated according to Table 3. If no l3 counters are present, behaviour remains unchanged.
Vlan interface entry is introduced, with IANA ifType 136

Snmpagent is extended with functions to update vlan interface list and rif to port mapping (using py-swsssdk utility functions).
  
# Testing

`test_snmp_interfaces.py` is covering the MIB. The test will be updated according to the MIB changes.

# Open questions
