# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for VNET monitoring.

# Requirements

The following are the high level requirements for the VNET monitoring infrastructure:
1. Any arbitrary pair of source ToR (SToR) and destination ToR (DToR) shall be able to send and recieve a data from and to VNET HW pipeline without using connected hosts.
2. The SToR shall be able to inject an overlay packet from a CPU port into the HW pipeline for further encapsulation and underlay routing.
3. The DToR shall be able to detect the injected packet after decapsulation and redirect it back to the SToR.

# SToR

The function of the SToR is to inject an overlay packet with the cookie for the DToR to trap and redirect back.
The cookie must be known to DToR ahead of time.

# DToR

The function of the DToR is to detect a packet from SToR by the cookie, swap SIP and DIP, and inject the packet back using the same mecahnism as DToR.

## Kernel configuration

For each VLAN interface, that is a member of the VNET, a kernel netdev representation is created.

```
SAI_HOSTIF_ATTR_TYPE = SAI_HOSTIF_TYPE_NETDEV;
SAI_HOSTIF_ATTR_OBJ_ID = port.m_vlan_info.vlan_oid;
SAI_HOSTIF_ATTR_NAME = <hostif_name>;
```

The netdev representations will reside in an assigned namespace.

```
ip netns add vnet
ip link set dev <hostif_name> netns vnet
```

## Supported interfaces

The VNET monitor supports packet injection into VLAN router interfaces.

## Sequence Number

The single SToR may send multiple ping requests to one or more DTORs and needs to distinguish between the responces.
For that a sequence number must be attached to the packet payload.


# Trigger mechanism

There are 3 possible packet events that can trigger the VNet mobitor to send the ping packet:
1. Periodic timer event - for each VNet for each DToR registered in the SToR
2. Controller event.
3. Recieving the packet from other ToR and generatig a reply as described in DToR section.

# Config DB Schema

TBD

# Init flow

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/Init.jpg)

# Packet event flow

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/PKT_EVENT.jpg)

# SToR packet walkthrough

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/DToR.jpg)

# DToR packet walkthrough

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/SToR.jpg)
