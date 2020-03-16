
# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for Proxy ARP support for VNet/Vxlan feature. 

# Requirements

The following are the proxy-arp requirements when an interface (currently intended for Vlan Interfaces) is associated to a VNET.

1. Proxy arp is enabled on the interface in kernel
2. Hardware ARP packet action for that interface must be trap to CPU and not flooded/forwarded in hardware.

The configuration must be removed, when interface is deleted. A VS test is required to validate the configuration

# Design Proposal

This section captures the design at a high-level and the configuration flows. 

When a configuration is applied as below, 

    "VLAN_INTERFACE": {
        "Vlan2000": {
             "vnet_name": "Vnet_3000"
	 }

proxy arp must be enabled in kernel for the following param:

```
/proc/sys/net/ipv4/conf/Vlan2000/proxy_arp_pvlan
```

The flow is as below for kernel setting

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/proxy_arp_kernel.png)

For requirement #2, the proposal is to disable flooding for the specific Vlan so that ARP packets shall not get flooded in hardware
By default in Sonic, it is a copy action for ARP packets which means, packets gets flooded in hardware. In the event of Vnet interfaces, flooding must be disabled. This enables the switch to respond to ARP requests within this subnet to be responded with its SVI mac. Currently, only the intforch is aware of the Vnet configuration, and hence must invoke the "Vlan flood" disable during the RIF creation.

The flow is as below for SAI setting

![](https://github.com/Azure/SONiC/blob/master/images/vxlan_hld/proxy_arp_flood.png)

# Additional Notes/Questions
1. The flooding is disabled only for those interfaces belonging to a Vnet. The implementation shall not modify the existing behavior for non-Vnet interfaces
2. What happens to unicast ARP requests?. Does this gets forwarded in hardware?
3. VS test can be added to existing ```test_vnet.py``` to verify the kernel/SAI configuration.
4. Proxy ND is not planned as part of this feature
5. ```/proc/sys/net/ipv4/conf/Vlan2000/proxy_arp``` is not required to be set.
6. Reference on Vnet/Vxlan design is [here](https://github.com/Azure/SONiC/blob/master/doc/vxlan/Vxlan_hld.md)

