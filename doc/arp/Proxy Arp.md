
# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for Proxy ARP support. 

# Requirements

The following are the high level requirements when an interface is enabled with "proxy_arp"

1. Proxy arp shall be set for the interface in kernel
2. Hardware ARP packet action for that interface must be trap to CPU and not flooded/forwarded in hardware.

When the interface is deleted, the corresponding configurations must be removed. A VS and sonic-mgmt test is required to validate the configuration

# Design Proposal

The design is intended to have a generic approach for proxy-arp feature. A user can set an attribute "proxy_arp" to the config_db entry for INTERFACE table entry. The default value if not specified would be "disabled"

The schema change for proxy-arp is as below:

```   
VLAN_INTERFACE|{{intf_name}} 
    "vnet_name": {{vnet_name}}
    "proxy_arp": "enabled"
          
VLAN_INTERFACE|{{intf_name}}|{{prefix}}  
    { }
```
```
; Defines Interface table schema

key             = INTERFACE:name         ; Same as existing
; field
vnet_name       = vnet_name              ; Same as existing
proxy_arp       = "enabled" / "disabled" ; Default "disabled" (Optional attribute)
```    

When proxy_arp is enabled for an interface, e.g

    "VLAN_INTERFACE": {
        "Vlan2000": {
             "vnet_name": "Vnet_3000"
             "proxy_arp": "enabled"
	 }

the following kernel param must be set to 1:

```
/proc/sys/net/ipv4/conf/Vlan2000/proxy_arp_pvlan
```

and SAI configuration for ```SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE``` must be set to ```SAI_VLAN_FLOOD_CONTROL_TYPE_NONE```

# Flows

The following flow diagram captures two example, one for user configuration and another for vnet interfaces

## Kernel config

![](https://github.com/sonic-net/SONiC/blob/master/images/vxlan_hld/proxy_arp_kernel.png)

## SAI config

For requirement #2, the proposal is to disable flooding for the specific Vlan so that ARP packets shall not get flooded in hardware.
By default in Sonic, it is a copy action for ARP packets which means, packets gets flooded in hardware. In the event of enabling proxy-arp, flooding must be disabled. This enables the switch to respond to ARP requests within this subnet to be responded with its SVI mac. ```Intforch``` must invoke "Vlan flood" disable during the RIF creation based on "prxoy_arp" attribute.

![](https://github.com/sonic-net/SONiC/blob/master/images/vxlan_hld/proxy_arp_flood.png)

# Additional Notes
1. The flooding is disabled only for those interfaces that has proxy_arp setting. The implementation shall not modify the existing behavior and shall be backward compatible. 
2. VS test can be added to existing ```test_vnet.py``` to verify the kernel/SAI configuration.
3. Proxy ND is not planned as part of this feature but can be extended in future based on the same approach
4. ```/proc/sys/net/ipv4/conf/Vlan2000/proxy_arp``` is not required to be set.
5. For non-Vlan interfaces, proxy_arp shall be set in kernel but no configuration is applied to SAI
6. Requires a sonic-mgmt test to verify the proxy-arp behaviour
