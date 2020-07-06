# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for VNET monitoring.

# Requirements

The following are the high level requirements for the VNET monitoring infrastructure:
1. Any arbitrary pair of source ToR (SToR) and destination ToR (DToR) shall be able to send and recieve a data from and to VNET HW pipeline without using connected hosts.
2. The SToR shall be able to inject an overlay packet from a CPU port into the HW pipeline for further encapsulation and underlay routing.
3. The DToR shall be able to detect the injected packet after decapsulation and redirect it back to the SToR.
4. The user interface to the monitoring tool is CLI based, e.g.:
```
vnet-ping <vnet_name> <ca_src_ip|optional> <ca_dst_ip>
```
5. Required input to the tool is:
   * Source VNET name to inject packet to
   * Optional BM src IP
   * BM dst IP
6. Connectivity is checked only in one direction from SToR to DToR. The way back should be checked from DToR

# SToR

The function of the SToR is to inject an overlay packet with the cookie and TTL=2 for the DToR to trap and redirect back.
The cookie must be known to DToR ahead of time.

# DToR

The function of the DToR is to detect a packet from SToR by the cookie, swap underlay SIP and DIP, and send it back to SToR

## Kernel configuration

For each VLAN interface, that is a member of the VNET, a kernel netdev representation is created.

```
SAI_HOSTIF_ATTR_TYPE = SAI_HOSTIF_TYPE_NETDEV;
SAI_HOSTIF_ATTR_OBJ_ID = port.m_vlan_info.vlan_oid;
SAI_HOSTIF_ATTR_NAME = <hostif_name>;
```

The netdev representations will reside in an assigned namespace (optional).

```
ip netns add vnet
ip link set dev <hostif_name> netns vnet
```

## Supported interfaces

The VNET monitor supports packet injection into VLAN router interfaces.


# SToR packet walkthrough

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/SToR.png)

1. inject packet to VLAN ID under source VNET
2. packet is classified to VNET VRF by VLAN RIF
3. overlay router looks up tunnel next hop
4. TTL is decremented to 1
5. VxLAN tunnel encap
6. underlay routing to DToR

# DToR packet walkthrough

![](https://github.com/marian-pritsak/sonic/blob/patch-2/doc/vxlan/DToR.png)

1. underlay routing
2. VxLAN decapsulation
3. packet is classified to VRF by VNI
4. overlay routing
5. "ttl too small" exception
6. packet redirection by vnet-pingd
