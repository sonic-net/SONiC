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

# DToR

TBD

# Trigger mechanism

TBD

# Config DB Schema

TBD
