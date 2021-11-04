# Interface Telemetry Subscribe

## Description    

The table below describes the subscription behavior for various paths and subscription types in the openconfig-interfaces.yang.    
Three subscription types are included, ON_CHANGE, SAMPLE and TARGET_DEFINED.
- both wildcard and non-wildcard can be used as the path key for ON_CHANGE
- only non-wildcard can be used as the path key for SAMPLE as of now

The top level paths are listed here for clarity, and all paths under the top level paths are included in the table unless specified otherwise.     
Note that the table only includes the paths that are being worked on by Dell and only ON_CHANGE enabled.

```
/oc-if:interfaces/oc-if:interface/oc-if:config
/oc-if:interfaces/oc-if:interface/oc-if:state
```

```
/oc-if:interfaces/oc-if:interface/oc-eth:ethernet/oc-eth:config
/oc-if:interfaces/oc-if:interface/oc-eth:ethernet/oc-eth:state except counters
/oc-if:interfaces/oc-if:interface/oc-eth:ethernet/oc-vlan:switched-vlan
```

```
/oc-if:interfaces/oc-if:interface/oc-lag:aggregation
/oc-if:interfaces/oc-if:interface/oc-lag:aggregation/oc-lag:config
/oc-if:interfaces/oc-if:interface/oc-lag:aggregation/oc-lag:state
/oc-if:interfaces/oc-if:interface/oc-lag:aggregation/oc-vlan:switched-vlan
```

```
/oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface/oc-ip:ipv4/oc-ip:addresses
/oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface/oc-ip:ipv4/oc-ip:neighbors
/oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface/oc-ip:ipv6/oc-ip:addresses
/oc-if:interfaces/oc-if:interface/oc-if:subinterfaces/oc-if:subinterface/oc-ip:ipv6/oc-ip:neighbors
```

```
/oc-if:interfaces/oc-if:interface/oc-vlan:routed-vlan/oc-ip:ipv4/oc-ip:addresses
/oc-if:interfaces/oc-if:interface/oc-vlan:routed-vlan/oc-ip:ipv4/oc-ip:neighbor
/oc-if:interfaces/oc-if:interface/oc-vlan:routed-vlan/oc-ip:ipv6/oc-ip:addresses
/oc-if:interfaces/oc-if:interface/oc-vlan:routed-vlan/oc-ip:ipv6/oc-ip:neighbors
```

```
/oc-if:interfaces/oc-if:interface/oc-intf:nat-zone
```

## Test case requirements
- cover all 3 subscribe types: ON_CHANGE, SAMPLE and TARGET_DEFINED.
- Within each subscribe type, cover all applicable paths
- negative test cases cover the paths not enabled for ON_CHANGE   

For example, for the path "/oc-if:interfaces/oc-if:interface/oc-if:config", test cases should cover
```
ON_CHANGE with wildcard for path key

- with uri "interfaces/interface[ifname=*]/config",
  check for name, type, mtu, description, enabled
- with uri "interfaces/interface[ifname=*]/config/name
  check for name
- with uri "interfaces/interface[ifname=*]/config/type
  check for type
- with uri "interfaces/interface[ifname=*]/config/mtu
  check for mtu
- with uri "interfaces/interface[ifname=*]/description
  check for description
- with uri "interfaces/interface[ifname=*]/enabled
  check for enabled
```

```
ON_CHANGE with specific interface name as path key

- with uri "interfaces/interface[ifname=Ethernet36]/config",
  check for name, type, mtu, description, enabled
- with uri "interfaces/interface[ifname=Ethernet36]/config/name
  check for name
- with uri "interfaces/interface[ifname=Ethernet36]/config/type
  check for type
- with uri "interfaces/interface[ifname=Ethernet36]/config/mtu
  check for mtu
- with uri "interfaces/interface[ifname=Ethernet36]/description
  check for description
- with uri "interfaces/interface[ifname=Ethernet36]/enabled
  check for enabled
```

```
SAMPLE (only with non-wildcard as path key for now)
- with uri "interfaces/interface[ifname=Ethernet36]/config",
  check for name, type, mtu, description, enabled
- with uri "interfaces/interface[ifname=Ethernet36]/config/name
  check for name
- with uri "interfaces/interface[ifname=Ethernet36]/config/type
  check for type
- with uri "interfaces/interface[ifname=Ethernet36]/config/mtu
  check for mtu
- with uri "interfaces/interface[ifname=Ethernet36]/description
  check for description
- with uri "interfaces/interface[ifname=Ethernet36]/enabled
  check for enabled
```

```
TARGET_DEFINED

- with uri "interfaces/interface[ifname=Ethernet36]/config",
  check for name, type, mtu, description, enabled
- with uri "interfaces/interface[ifname=Ethernet36]/config/name
  check for name
- with uri "interfaces/interface[ifname=Ethernet36]/config/type
  check for type
- with uri "interfaces/interface[ifname=Ethernet36]/config/mtu
  check for mtu
- with uri "interfaces/interface[ifname=Ethernet36]/description
  check for description
- with uri "interfaces/interface[ifname=Ethernet36]/enabled
  check for enabled
```

## Interface Subscription Paths    

* rej: subscribe is rejected    
* disallow: modification or delete of the YANG leaf is disallowed    


|                                                                             | ON_CHANGE    |        |        | SAMPLE | TARGET_DEFINED |
| --------------------------------------------------------------------------- | ------------ | ------ | ------ | ------ | --------------- |
|                                                                             | initial sync | update | delete |        |                 |
| openconfig-interfaces:interfaces/interface[name=*]                                                       | N(rej)    | N(rej) | N (rej)      |       |                 |
| openconfig-interfaces:interfaces/interface[name=*]/config                                              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/config/name                                                                | Y            | N(disallow)      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/config/type                                                                 | Y            | N(disallow)      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/config/mtu                                                                  | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/config/description                                                          | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/config/enabled                                                              | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state                                               | N(rej)            | N(rej)      | N(rej)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/name                                                                  | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/mtu                                                                   | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/description                                                           | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/enabled                                                               | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/admin-status                                                         | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/state/oper-status (only appl. to Ethernet)                                  | Y            | Y      | Y      |        |                 |
| openconfig-interfaces:interfaces/interface[name=*]/state/rate-interval      | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config/auto-negotiate(only appl. to mgmt port)         | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config/port-speed                                       | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config/aggregate-id( only appl. to Ethernet)            | N(rej)            | N(rej)      | N(rej)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config/port-fec(only appl. to Ethernet)                                     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/config/port-unreliable-los (only appl. to Ethernet)     | N(disallow)            | N(disallow)      | N(disallow)      | Y      | Y         |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/state                                                | N(rej)            | N(rej)      | N(rej)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/state/auto-negotiate(only appl. to mgmt port)                           | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/state/port-speed                                                        | Y            | Y      | N(disallow)      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethenet/state/aggregate-id( only appl. to Ethernet port)                            | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/state/port-fec(only appl. to Ethernet)                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/state/port-unreliable-los (only appl. to Ethernet)                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switched-vlan                                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switch-vlan/config                                           | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switch-vlan/config/interface-mode                                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switch-vlan/config/access-vlan                                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switch-vlan/config/trunk-vlans                                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switched-vlan/state                                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switched-vlan/state/interface-mode                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switched-vlan/state/access-vlan                                         | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-ethernet:ethernet/switched-vlan/state/trunk--vlans                                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan                                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/config                             | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/config/interface-mode                                 | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/config/access-vlan                                    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/config/trunk-vlans                                    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/state                               | Y            | Y      | N      | N      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/state/interface-mode                                  | Y            | Y      | N      | N      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/state/access-vlan                                     | Y            | Y      | N      | N      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/switched-vlan/state/trunk--vlans                                    | Y            | Y      | N      | N      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config                                           | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config/minlinks                                                     | Y            | N(disallow)      | Y     | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config/graceful-shutdown-mode                                       | Y            | Y      | Y      |  Y     | Y      |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config/lag-type                                                     | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config/fallback                                                     | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/config/fast-rate                                                    | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state                                             | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/minlinks                                                      | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/graceful-shutdown-mode                                        | N            | N(disallow)      | Y      |        |                 |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/lag-type                                                      | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/fallback                                                      | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/fast-rate                                                     | Y            | N(disallow)      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-if-aggregate:aggregation/state/member                                                                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4                                                | N(rej)            | N(rej)      | N(rej)      | N(rej)      | N(rej)               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses                                              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]                                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/config                         | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/ip     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/prefix-length           | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/secondary               | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/state                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/ip                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/prefix-length            | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/secondary                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6                                                | N(rej)            | N(rej)      | N(rej)      | N(rej)      | N(rej)               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses                                              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]                                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/config                         | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/config/ip                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/config/secondary               | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/state                          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/state/ip                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/addresses/address[ip=*]/state/prefix-length            | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4                                 | N(rej)            | N(rej)      | N(rej)      | N(rej)      | N(rej)               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/config                 | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/ip              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/prefix-length   | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/config/secondary       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/state                  | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/ip               | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/prefix-length    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/addresses/address[ip=*]/state/secondary        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6                                 | N(rej)            | N(rej)      | N(rej)      | N(rej)      | N(rej)               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/config                 | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/config/ip              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/config/secondary       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/state                  | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/state/ip               | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/addresses/address[ip=*]/state/secondary        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]config                   | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/config/ip                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/config/link-layer-address   | Y              |Y        | Y       | Y        | Y                |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state                     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state/ip                | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state/link-layer-address      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors                                      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]                                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/config                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]config/ip                     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/config/link-layer-address    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state/ip                    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/openconfig-vlan:routed-vlan/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state/link-layer-address    | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors                        | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]         | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/config  | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/config/ip              | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/config/link-layer-address     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state           | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state/ip       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv4/neighbors/neighbor[ip=*]/state/link-layer-address      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors                  | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]   | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/config   | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/config/ip      | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/config/link-layer-address     | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state           | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state/ip                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/openconfig-if-ip:ipv6/neighbors/neighbor[ip=*]/state/link-layer-address       | Y            | Y      | Y      | Y      | Y               |
| Note: for neighbor "update" under ON\_CHANGE, only new values are received, not the deleted ones |              |        |        |        |                 |
| openconfig-interfaces:interfaces/interface[name=*]/nat-zone                                                       | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/nat-zone/config         | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/nat-zone/config/nat-zone          | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/nat-zone/state            | Y            | Y      | Y      | Y      | Y               |
| openconfig-interfaces:interfaces/interface[name=*]/nat-zone/state/nat-zone   | Y            | Y      | Y      | Y      | Y               |


# NTP telemetry subscribe

*rej: subscribe rejected

|                                                                             | ON_CHANGE    |        |        | SAMPLE | TARGET_DEFINED |
| --------------------------------------------------------------------------- | ------------ | ------ | ------ | ------ | --------------- |
|                                                                             | initial sync | update | delete |        |                 |
| openconfig-system:system/ntp                                                | N (rej)	     | N(rej) | N(rej) | Y      |  Y              |
| openconfig-system:system/ntp/config                                         | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/config/enabled                                 | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/config/enable-ntp-auth                         | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/config/trusted-key                             | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/config/source-interface                        | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/config/network-instance                        | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state                                          | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state/enabled                                  | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state/enable-ntp-auth                          | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state/trusted-key                              | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state/source-interface                         | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/state/network-instance                         | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys                                       | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-key[key-id=*]                     | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-key[key-id=*]/config              | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-key[key-id=*]/config/key-id       | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/config/key-type     | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/config/key-value    | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/config/encrypted    | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-key[key-id=*]/state               | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-key[key-id=*]/state/key-id        | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/state/key-type      | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/state/key-value     | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/ntp-keys/ntp-kdy[key-id=*]/state/encrypted     | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/servers                                        | N(rej)       | N(rej) | N(rej) | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]                      | N(rej)       | N(rej) | N(rej) | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/config               | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/config/address       | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/config/key-id        | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/config/minpoll       | Y            | Y      | N(default exists)      | Y      |  Y        |     
| openconfig-system:system/ntp/servers/server[address=*]/config/maxpoll       | Y            | Y      | N(default exists)      | Y      |  Y        |    
| openconfig-system:system/ntp/servers/server[address=*]/state                | N(rej)       | N(rej) | N(rej) | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/state/address        | Y            | Y      | Y      | Y      |  Y              |                           
| openconfig-system:system/ntp/servers/server[address=*]/state/key-id         | Y            | Y      | Y      | Y      |  Y              |
| openconfig-system:system/ntp/servers/server[address=*]/state/minpoll        | Y            | Y      | N(default exists)      | Y      |  Y        |                                  
| openconfig-system:system/ntp/servers/server[address=*]/state/maxpoll        | Y            | Y      | N(default exists)      | Y      |  Y        |
| openconfig-system:system/ntp/servers/server[address=*]/state/refid          | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/stratum        | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/peer-type      | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/when           | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/poll-interval  | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/reach          | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/peer-delay     | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |  
| openconfig-system:system/ntp/servers/server[address=*]/state/peer-offset    | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |
| openconfig-system:system/ntp/servers/server[address=*]/state/peer-jitter    | N(rej)       | N(rej) | N(rej) | N(not in DB)      |  N   |

# VRF config/state and interface/VRF binding telemetry subscribe    

* rej: subscribe rejected
* disallow: leaf change disallowed

|                                                                             | ON_CHANGE    |        |        | SAMPLE | TARGET_DEFINED |
| --------------------------------------------------------------------------- | ------------ | ------ | ------ | ------ | --------------- |
|                                                                             | initial sync | update | delete |        |                 |
| openconfig-network-instance:network-instances                               | N(rej)       | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]      | N(rej)       | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/config    | Y        | Y      | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/config/name    | Y        | N(disallow)      | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/config/type    | Y        | N(disallow)     | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/config/enabled    | Y        | Y      | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/state    | Y        | Y      | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/state/name    | Y        | N(disallow)      | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/state/type    | Y        | N(disallow)     | Y      | Y      | Y               |
| openconfig-network-instance:network-instances/network-instance[name=*]/state/enabled    | Y        | Y      | Y      | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces        | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]        | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/config        | Y   | Y | Y | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/config/id        | Y   | Y | Y | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/config/interface        | Y   | Y | Y | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/config/subinterface     | Y   | Y | Y | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/state        | N(rej)   | N(rej) | N(rej) | Y      | Y               |   
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/state/id        | N(rej)   | N(rej) | N(rej) | Y      | Y               |           
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/state/interface        | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=*]/interfaces/interface[id=*]/state/subinterface     | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]        | N(rej)   | N(rej) | N(rej) | Y      | Y               |                
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/config        | Y   | Y | Y | Y      | Y               |                 
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/config/id        | Y   | Y | Y | Y      | Y               |             
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/config/interface        | Y   | Y | Y | Y      | Y               |              
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/config/subinterface     | Y   | Y | Y | Y      | Y               |              
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/state        | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/state/id        | N(rej)   | N(rej) | N(rej) | Y      | Y               |     
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/state/interface        | N(rej)   | N(rej) | N(rej) | Y      | Y               |
| openconfig-network-instance:network-instance/network-instance[name=Vrf_1]/interfaces/interface[id=*]/state/subinterface     | N(rej)   | N(rej) | N(rej) | Y      | Y               |    



# BGP OC-Paths for ONCHANGE and Wildcard


BGP on change support has been provided for 2 yang models by Dell.
1.	openconfig-network-instance.yang  for BGP protocol under protocols.
2.	openconfig-routing-policy.yang for defined-sets and policy-definitions.

There are various RedisDB config tables monitored to provide the ON_CHANGE support. There are some nodes where the state information is fetched from FRR container via “vtysh” command execution. These nodes don’t support ON_CHANGE.
Below is the list of openconfig-yang  paths supporting  ON_CHANGE and also those not-supporting ON_CHANGE. The supported path refers to the parent node and all child nodes under it will support on_change. All the children under a supported path will not be mentioned as its huge but can be referred from the open-config-yang model tree. If a node is mentioned to not-support ON_CHANGE , all child node under it will also not support on_change.
NOTE: SAMPLE is supported for all the supported paths without  a wildcard. TARGET_DEFINED is also supported but defaults to ON_CHANGE subscription.


openconfig-network-instance.yang can be broadly divided in to 4 subgroups for BGP protocol
1.	global:-


|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n)  |  
| ---------------------------------------------------------------------------      | -------------|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/config"| y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/confederation/"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/graceful-restart/"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/use-multiple-paths/"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/route-selection-options/"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/config"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/use-multiple-paths"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/aggregate-address-config"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/network-config"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/default-route-distance"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/route-flap-damping"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/openconfig-bgp-ext: import-network-instance"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/dynamic-neighbor-prefixes"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/logging-options"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/route-reflector"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/global-defaults"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/update-delay"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/max-med"| y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/state"|n|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/global/afi-safis/afi-safi[afi-safi-name=*]/l2vpn-evpn”|n|

2.	neighbors:-

 |     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
 | ---------------------------------------------------------------------------      | -------------|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/config"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/timers”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/transport”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/ebgp-multihop”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/enable-bfd”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/auth-password”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/config”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/add-paths”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/apply-policy”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/ipv4-unicast|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/ipv6-unicast"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/allow-own-as"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-saf-ame=*]/attribute-unchanged”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-saf-name=*]/next-hop-self”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-saf-name=*]/prefix-list”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-saf-name=*]/remove-private-as”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-saf-name=*]/capability-orf”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/state”|n|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/timers/state”|n
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/transport/state”|n
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/state”|n|

3.	peer-group:-

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
| ---------------------------------------------------------------------------      | -------------|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/config"|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/state”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/transport”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/ebgp-multihop”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/auth-password”|y|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/members-state/config”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/config”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/state”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/add-paths”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/apply-policy”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/ipv4-unicast"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/ipv6-unicast"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/allow-own-as"|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-ame=*]/attribute-unchanged”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-name=*]/filter-list”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-name=*]/next-hop-self”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-name=*]/prefix-list”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-name=*]/remove-private-as”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-saf-name=*]/capability-orf”|y|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/enable-bfd”|y|
|"/openconfig-network-instance:network-instances/network-instance[name={}]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/members-state/state”|n|
|“/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/peer-groups/peer-group[peer-group-name=*]/afi-safis/afi-safi[afi-safi-name=*]/l2vpn-evpn”|n|

4.	rib:- this is not supported for on_change

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
| ---------------------------------------------------------------------------      | -------------|
|"/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=bgp]/bgp/rib”|n|


  #### openconfig-routing-policy.yang:-  

It can be broadly divided in to 2 groups. Parent and some important child groups are mentioned. Currently on_change is supported for all nodes in openconfig-routing-policy.yang. The state info is fetched same as config info.
1.	defined-sets:

“/openconfig-routing-policy:routing-policy/defined-sets/”  supports ON_CHANGE

Following are important child nodes under “/openconfig-routing-policy:routing-policy/defined-sets/”

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
| ---------------------------------------------------------------------------      | -------------|
| “/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=*]”|y|
|“/openconfig-routing-policy:routing-policy/defined-sets/prefix-sets/prefix-set[name=*]/openconfig-routing-policy-ext:prefixes-ext/prefix[sequence-number=*][ip-prefix=*][masklength-range=*]”|y|
|“/openconfig-routing-policy:routing-policy/defined-sets/openconfig-bgp-policy:bgp-defined-sets/community-sets/community-set[community-set-name=*]”|y|
|"/openconfig-routing-policy:routing-policy/defined-sets/openconfig-bgp-policy:bgp-defined-sets/community-sets/community-set[ext-community-set-name=*]”|y|
|“/openconfig-routing-policy:routing-policy/defined-sets/openconfig-bgp-policy:bgp-defined-sets/as-path-sets/as-path-set[as-path-set-name=*]”|y|
|“/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]”|y|

2.	policy-definitions:

"openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]” supports ON_CHANGE

Following are important child nodes under “/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]”

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
|---------------------------------------------------------------------------| -------------|
|“/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]/statements”|y|
|“/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]/statements/statement[name=*]”|y|
|“/openconfig-routing-policy:routing-policy/policy-definitions/policy-definition[name=*]/statements/statement[name=*]/actions”|y|


# DNS OC-Paths for ONCHANGE and Wildcard

DNS on change support has been provided for openconfig-system.yang model by Dell.
There are 2 RedisDB config tables monitored to provide the ON_CHANGE support for system DNS.
The table names are listed below
1.	DNS : This is used to store global values.
2.	DNS_SERVER : This is used to store dns server details
Below is the list of openconfig-yang  paths supporting  ON_CHANGE and also those not-supporting ON_CHANGE. The supported path refers to the parent node and all child nodes under it will support on_change. All the children under a supported path will not be mentioned as its huge but can be referred from the open-config-yang model tree. If a node is mentioned to not-support ON_CHANGE , all child node under it will also not support on_change.

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n) |  
|---------------------------------------------------------------------------| -------------|
|"/openconfig-system:system/dns/config"|y|
|"/openconfig-system:system/dns/servers/server[address={}]/config"|y|
|"/openconfig-system:system/dns/state"|n|
|"/openconfig-system:system/dns/servers/server[address={}]/state"|n|

# Static Route OC-Paths for ON-CHANGE and Wildcard

## Description

Static Route on change support has been provided for openconfig-local-routing.yang mode by Dell.
RedisDB config table STATIC_ROUTE was monitored to provide the ON-CHANGE support for static route with next-hop configurations.
Below is the list of openconfig-yang paths supporting ON-CHANGE supscription for static-route feature. That includes the root path "/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes" and its children nodes defined in OC-YANG:

|     Paths                                                                        | ON_CHANGE Supported yes(y)/no(n)  |
| ---------------------------------------------------------------------------      | -------------|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/prefix| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/config| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/config/prefix| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/state| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/state/prefix| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/index| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/index| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/next-hop| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/metric| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/tag| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/track| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/network-instance| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/config/blackhole| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/index| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/next-hop| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/metric| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/tag| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/track| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/network-instance| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/state/blackhole| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/openconfig-interfaces:interface-ref/config/interface| y|
|/openconfig-network-instance:network-instances/network-instance[name=*]/protocols/protocol[identifier=STATIC][name=static]/static-routes/static[prefix=*]/next-hops/next-hop[index=*]/openconfig-interfaces:interface-ref/state/interface| y|
