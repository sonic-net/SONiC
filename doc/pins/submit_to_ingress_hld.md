# Submit to Ingress HLD

## Table of Content

* [Table of Content](#table-of-content)
* [Revision](#revision)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitions-abbreviations)
* [Overview](#overview)
  + [Direct transmit](#direct-transmit)
  + [Ingress pipeline inject](#ingress-pipeline-inject)
* [Requirements](#requirements)
* [Architecture Design](#architecture-design)
* [High-Level Design](#high-level-design)
  + [CONFIG DB schema](#config-db-schema)
  + [SWSS](#swss)
  + [Multi-Asic consideration](#multi-asic-consideration)
* [SAI API](#sai-api)
* [Configuration and management](#configuration-and-management)
  + [CLI/YANG model Enhancements](#cli-yang-model-enhancements)
  + [Config DB Enhancements](#config-db-enhancements)
* [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
* [Restrictions/Limitations](#restrictions-limitations)
* [Testing Requirements/Design](#testing-requirements-design)
  + [Unit Test cases](#unit-test-cases)
  + [System Test cases](#system-test-cases)
* [Open/Action items - if any](#open-action-items---if-any)

## Revision

Rev  | Rev Date   | Author(s)              | Change Description
---- | ---------- | -----------------------| ------------------
v0.1 | 04/01/2022 | Yilan Ji, Stephen Wang | Initial version

## Scope

Submit to ingress feature in GPINs is to support [Packet I/O](https://github.com/Azure/SONiC/blob/master/doc/pins/Packet_io.md) transmit path that injects packets into the dataplane by the CPU. This doc is to redesign Packet I/O Transmit Path.

## Definitions/Abbreviations

**PINS**: P4 Integrated Network Stack (PINS) provides a remote interface to SAI using P4.

## Overview

Packet I/O transmit involves taking care of 2 types of packets that have to be transmitted: Direct transmit and Ingress pipeline inject.

### Direct transmit

If the sender(applications like LACP or P4RT) already know the egress port that the packet should be sent out on, it is done by placing the packet on the socket interface of the corresponding netdev interface.  

### Ingress pipeline inject

In the SDN scenario, the controller has the complete view of the whole network and programs the switch ASIC with the optimized routing rules that the switch NOS is not aware of. Also in some other scenario, that the ASIC has a better understanding of the current bandwidth/queue depth of each port that it can choose a better egress port from the ECMP/WCMP group. The sender application on the switch would like to inject the packet to the ASIC’s ingress pipeline to allow the switch ASIC to make the final decision.

Injecting packets to the ingress pipeline can also be used as a way to test ASIC routing behavior in the standalone test environment.

## Requirements

* Provide configuration support of submit to ingress in the port table.

## Architecture Design

![drawing](images/submit_to_ing.png)

Details of the transmit path in GPINs Packet I/O can be found in this [HLD](https://github.com/Azure/SONiC/blob/master/doc/pins/Packet_io.md#transmit-path).

## High-Level Design

This HLD introduces a new “Submit To Ingress” port type in the port table that SWSS will create a corresponding netdev/host interface. Any application can inject the packet to the ASIC’s ingress pipeline and let the ASIC decide which port to send packet out based on the routing table and current state of the network.

### CONFIG DB schema

Add knob in PORT table in CONFIG DB or config_db.json to enable submit to ingress

```
  "PORT": {
    "Ethernet0": {
      "admin_status": "up",
      "alias": "NoAliasEth0/1",
      "index": "1",
      "lanes": "9,10,11,12,13,14,15,16",
      "mtu": "9100",
      "speed": "400000"
    },
    …
    "SUBMIT_TO_INGRESS": {}  
 }
```

### SWSS

1. PortsMgr process PORT|SUBMIT_TO_INGRESS in config_db.json during initialization, or add/delete the PORT|SUBMIT_TO_INGRESS entry in CONFIG DB during runtime by mapping it to APPL_DB PORT_TABLE:SUBMIT_TO_INGRESS table entry.
2. PortsOrch then picks up the entry in PORT_TABLE and calls sai_hostif_api->create_hostif or `sai_hostif_api->delete_hostif` to  add/delete the submit_to_ingress netdev.

```
sai_attribute_t attr;
vector<sai_attribute_t> &ingress_attribs;
            
attr.id = SAI_HOSTIF_ATTR_TYPE;
attr.value.s32 = SAI_HOSTIF_TYPE_NETDEV;
ingress_attribs.push_back(attr);

attr.id = SAI_HOSTIF_ATTR_NAME;
auto size = sizeof(attr.value.chardata);
strncpy(attr.value.chardata, submit_to_ingress_name.c_str(), size - 1);
attr.value.chardata[size - 1] = '\0';
ingress_attribs.push_back(attr);

// If this isn't passed in true, the false setting makes
// the device unready for later attempts to set UP/RUNNING
attr.id = SAI_HOSTIF_ATTR_OPER_STATUS;
attr.value.booldata = true;
ingress_attribs.push_back(attr);

// Get CPU port object id to signal submit to ingress
attr.id = SAI_SWITCH_ATTR_CPU_PORT;
auto status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Unable to get CPU port");
    return false;
}

attr.id = SAI_HOSTIF_ATTR_OBJ_ID;
ingress_attribs.push_back(attr);

sai_status = sai_hostif_api->create_hostif(&m_submit_to_ingress_id,
                                               gSwitchId,
                                               (uint32_t)ingress_attribs.size(),
                                               ingress_attribs.data()
                                               );
```

SUBMIT_TO_INGRESS port adds a netdev, aligned with the behavior as the other ports in the PORT table in CONFIG DB. Users can choose to enable the SUBMIT_TO_INGRESS port or not by editing the PORT table. In PortsOrch/PortsMgr, the new port naming SUBMIT_TO_INGRESS is different from the known port types with prefix Vlan or Ethernet, so it can be treated differently as a new type.

### Multi-Asic consideration

Per [SONiC multi asic HLD](https://github.com/Azure/SONiC/blob/master/doc/multi_asic/SONiC_multi_asic_hld.md), each ASIC will have its own replica of SWSS/SYNCD and configuration. So each ASIC can create its own submit to ingress port. Each netdev will be in their own namespace.

## SAI API

N/A

## Configuration and management

New configuration of submit to ingress will be added in the port table as mentioned in the design.

### CLI/YANG model Enhancements

N/A

### Config DB Enhancements

N/A

## Warmboot and Fastboot Design Impact

N/A

## Restrictions/Limitations

N/A

## Testing Requirements/Design


### Unit Test cases

PortsMgr and PortsOrch behaviors will be tested in swss pytest.

### System Test cases

System Packet I/O behaviors will be tested in Thinkit end-to-end testing.

## Open/Action items - if any

N/A
