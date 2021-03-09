# Recycle port support on VOQ chassis

# High Level Design Document
#### Rev 1

# Table of Contents
* [List of Tables](#list-of-tables)
* [List of Figures](#list-of-figures)
* [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
* [Definitions/Abbreviations](#definitionsabbreviations)
* [1 Design](#1-design)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviations)

# List of Figures

# Revision
| Rev |     Date    |       Author       | Change Description |      
|:---:|:-----------:|:------------------:|--------------------|
| 1 | Jan-25 2021 | Song Yuan, Eswaran Baskaran (Arista Networks) | Initial Version |

# About this manual

This document provides an overview of the SONiC support for recycle ports in a VOQ-based chassis. In a VOQ-based chassis, the packet received by one chip (i.e., the ingress chip) can be forwarded out of another chip (i.e., the egress chip). This inter-chip forwarding generally requires co-ordinating the programming of the egress chip (with the correct rewrite data) and the ingress chip. The recycle port, a special port for which the egress of the port is looped back to the ingress, makes it possible to achieve the inter-chip forwarding without co-ordinating the programming of the egress chip along with the ingress chip.

# Scope

The goal of this document is to describe the design of SONIC support for recycle ports in a VOQ-based chassis. 

# Definitions/Abbreviations

|      |                    |                                |
|------|--------------------|--------------------------------|
| ASIC | Application Specific Integrated Circuit | Refers to the forwarding engine on a device that is responsible for packet forwarding. |


# 1 Design
A packet sent to a recycle port is looped back to the ingress pipeline of the ASIC where the recycle port belongs to. Once the packet comes back to the ingress pipeline again, it will be forwarded to the egress ASIC where the packet gets switched out of the destination port. 

The figure below shows an example of the forwarding path via recycle port.

![](../../images/recycle_port_hld/recycle_port.png)

The packet sent to the recycle port can either originate from the network, e.g., as shown in the above figure, or received from a local kernel interface. The packet sent to a recycle port needs to be correctly crafted or rewritten, e.g., having the correct DMAC or destination IP. Otherwise, it won’t be forwarded correctly when it comes into the ingress pipeline again. 

## 1.1 Recycle-to-bridged vs. Recycle-to-routed

Depending on the DMAC of the recycled packet and the configuration of the recycle port, the packet coming out from recycle port can either bridged (i.e., recycle-to-bridged) or routed (i.e., recycle-to-routed) in the ingress ASIC. If the DMAC is not the router MAC of the ingress ASIC, the packet is bridged according to its DMAC. If the DMAC is router MAC and the recycle port is configured as a routed port, the packet will be routed based on the destination IP of the rewritten packet.

To ensure the recycled packet is bridged/routed correctly, the corresponding FDB or route entry must be programmed in the ingress ASIC. 

In general, recycle-to-routed is more preferred to reccyle-to-bridged because the former can take the advantages of L3 forwarding features like ECMP. However, recycle-to-routed is also having its own limitation/issue. For example, the TTL of the egress packet may be decremented twice because the packet is routed twice.

## 1.2 Explict recycle ports

Since the traffic is forwarded via recycle ports, it’s ideal to have statistics, like counters or errors, collected for recycle ports as well just like for front panel ports. This makes it easier to debug forwarding issue in which recycle ports are involved. To this end recycle ports need to be made visible to SONiC.

The support of explicit recycle ports requires the minimal changes to SAI as long as recycle ports can be created. SONiC discovers the recycle ports just like front panel ports and explicitly passes the recycle ports (precisely their SAI port Ids) in SAI calls if needed.

## 1.3 Configuration of recycle ports

Recycle ports are configured in port_config.ini just like front panel ports. In order to distinguish recycle from front panel ports, the appropriate port role must be set for recycle ports. The port role must indicate the intended use of a recycle port. SONiC can discover all configured recycle ports, based on their port roles, and use them appropriately.

As of now, there are two use cases of recycle ports: inband port [here](https://github.com/Azure/SONiC/blob/master/doc/voq/architecture.md), or features like Everflow that needs to recycle encapsulated packets to be routed to the egress ASIC [here](https://github.com/Azure/SONiC/pull/716/files). In order to ensure the right recycle ports are used, we introduce two port roles, Inb and Rec, for the two use cases respectively.

Two recycle ports, Ethernet-Rec0 and Ethernet-IB0, are configured in the example port_config.ini below. Ethernet-Rec0 is used by Everflow, which has port role Rec. Ethernet-IB0 is used as an inband port and thus its port role is set to Inb. The recycle port's lanes, used to discover the corresponding SAI ports, must be provided in port_config.ini as well.

```
#name               lanes                     alias        index  role       speed
Ethernet0           48,49,50,51,52,53,54,55   Ethernet1/1  1      Ext        400000
Ethernet8           56,57,58,59,60,61,62,63   Ethernet2/1  2      Ext        400000
Ethernet16          64,65,66,67,68,69,70,71   Ethernet3/1  3      Ext        400000
Ethernet24          72,73,74,75,76,77,78,79   Ethernet4/1  4      Ext        400000
Ethernet-Rec0       221                       Recirc0/0    5      Rec        400000
Ethernet-IB0        222                       Recirc0/1    6      Inb        400000
```

The process of recycle ports in SWSS container is similar to front panel ports: portsyncd populates recycle ports into APPL_DB PORT_TABLE; portsorch discovers, initializes recycle ports, and adds host interfaces for them; and intfsorch adds router interfaces for recycle ports.
