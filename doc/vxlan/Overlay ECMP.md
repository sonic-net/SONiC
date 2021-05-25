# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for Overlay ECMP support. 

# Requirements

The following are the high level requirements for enabling overlay ecmp

1. User shall be able to create a VNET in default scope, thus enabling route lookup in the default VRF tables.
2. User shall be able to specify multiple endpoints for a route prefix
3. User shall be able to specify different weights for the endpoints. Higher value means more preferred nexthop. 
4. User shall be able to modify the endpoints for a route prefix

A VS and sonic-mgmt test is required to validate overlay ECMP feature.

# Design Proposal

## Schema

The schema changes for overlay ECMP based VNET routes is as below: For creating a default VNET, user must provide the name as "Vnet-default".

### VNET schema
```
VNET|{{vnet_name}} 
    "vxlan_tunnel": {{tunnel_name}}
    "vni": {{vni}} 
    "scope": {{default}} (OPTIONAL)
```

### Existing schema for route
```   
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address}} 
    "mac_address":{{mac_address}} (OPTIONAL) 
    "vni": {{vni}} (OPTIONAL) 
```

### Proposed schema for route
```
VNET_ROUTE_TUNNEL_TABLE:{{vnet_name}}:{{prefix}} 
    "endpoint": {{ip_address1},{ip_address2},...} 
    "mac_address":{{mac_address1},{mac_address2},...} (OPTIONAL) 
    "vni": {{vni1},{vni2},...} (OPTIONAL)
    "weight": {{w1},{w2},...} (OPTIONAL)
```

; Defines schema for VNET route tunnel table attributes
```
key                                   = VNET_ROUTE_TUNNEL_TABLE:vnet_name:prefix ; Vnet route tunnel table with prefix
; field                               = value
ENDPOINT                              = list of ipv4 addresses        ; comma seperated list of endpoints
MAC_ADDRESS                           = 12HEXDIG                      ; Inner dest mac in encapsulated packet, comma seperated (Optional)
VNI                                   = DIGITS                        ; VNI value in encapsulated packet, comma seperated (Optional)
WEIGHT                                = DIGITS                        ; Weights for the nexthops, comma seperated (Optional)
```    
## RestAPI

### Current API for non-ECMP route add
```
curl --request PATCH -H "Content-Type:application/json" -d 
    '[{"cmd":"add", "ip_prefix":"10.0.1.10/32", "nexthop":"100.3.152.32","vnid":2, "mac_address":"00:08:aa:bb:cd:10"}]' 
     http://10.3.146.62:8090/v1/config/vrouter/vnet-guid-1/routes
```

### API for ECMP routes

Case #1: Add Multiple Endpoints
```
curl --request PATCH -H "Content-Type:application/json" -d 
    '[{"cmd":"add", "ip_prefix":"10.0.1.10/32", "nexthop":"100.3.152.32,200.3.152.32","vnid":"2,3", "mac_address":"00:08:aa:bb:cd:10,00:08:cc:dd:ef:10"}]'
     http://10.3.146.62:8090/v1/config/vrouter/Vnet-default/routes
```
Case #2: Add Multiple Endpoints, with optional vni/mac_address (Empty string for positional arguments)
```
curl --request PATCH -H "Content-Type:application/json" -d 
    '[{"cmd":"add", "ip_prefix":"20.0.1.10/32", "nexthop":"101.3.152.32,201.3.152.32","vnid":"2,", "mac_address":",00:09:dd:ee:ef:10", "weight":"20,10"}]'
     http://10.3.146.62:8090/v1/config/vrouter/Vnet-default/routes
```
Case #3: Modify Endpoints
```
curl --request PATCH -H "Content-Type:application/json" -d 
    '[{"cmd":"add", "ip_prefix":"10.0.1.10/32", "nexthop":"100.3.152.32,201.3.152.32"}]'
     http://10.3.146.62:8090/v1/config/vrouter/Vnet-default/routes
```
Case #4: Delete Route
```
curl --request PATCH -H "Content-Type:application/json" -d 
    '[{"cmd":"delete", "ip_prefix":"10.0.1.10/32", "nexthop":"100.3.152.32,201.3.152.32"}]'
     http://10.3.146.62:8090/v1/config/vrouter/Vnet-default/routes
```

## SWSS and SAI 

Following changes are required for overlay ECMP support in SWSS. Corresponding SAI and HW support is required to program Vxlan Tunnel based Nexthop groups.

1. Vnetorch to add support to handle multiple endpoints for APP_VNET_RT_TUNNEL_TABLE_NAME based route task
2. Reuse Nexthop tunnel based on the endpoint configuration. If there is already the same endpoint exists, use that as member for Nexthop group.
3. Similar to above, reuse nexthop group, if multiple routes are programmed with the same set of nexthops. 
4. Handle support for endpoint modification for a route prefix. Require SAI support for SET operation of routes.
5. Ensure backward compatibility with single endpoint routes
6. Use SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT for specifying weights to nexthop member

## Open questions

1. Does the routes needs to be persistant? 
2. What are the requirements to advertise the routes?
3. How many VNETs/Routes are expected to be programmed?
4. Will user modify the routes OR only delete and re-add?
5. What are the requirements for vxlan source port range?
6. What are the devices roles (T1, T0..) that require overlay ecmp support?
7. What are the requirements for V6 routes over V4 tunnels or vice-versa?
