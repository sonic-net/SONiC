# W-ECMP Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| SONiC Weighted ECMP | [https://github.com/nazariig/SONiC/blob/773aacaeb7a6e5507af667898957b2060a78280e/doc/wcmp/wcmp-design.md]|

## Overview
In ECMP (Equal-Cost Multi-Path) scenario, traffic is distributed equally across all available paths and each path has same cost.

In W-ECMP (Weighted-Cost Multi-Path) scenario, it can distribute traffic base on the weight value assigned to each path. This is useful when the paths have different bandwidth capacities. In a W-ECMP setup, each path is assigned a weight based on various criteria, such as bandwidth, delay, or administrative preferences. BGP then uses these weights to distribute outbound traffic among the multiple available paths


## BGP link bandwidth extended community
The BGP link bandwidth extended community contains information about the bandwidth of a link. This information is advertised along with BGP route updates to inform other routers about the capacity of the link.
RFC: [https://datatracker.ietf.org/doc/html/draft-ietf-idr-link-bandwidth]

```
router bgp 65200
 bgp router-id 10.1.0.2
 no bgp ebgp-requires-policy
 neighbor SPINE1 peer-group
 neighbor SPINE1 remote-as 65100
 neighbor 10.10.1.1 peer-group SPINE1
 neighbor 10.10.2.1 peer-group SPINE1
 !
 address-family ipv4 unicast
  network 20.20.20.0/24
  neighbor SPINE1 route-map TO_BGP_PEER_V4 out      <<<<<<
 exit-address-family
exit
!
route-map TO_BGP_PEER_V4 permit 100
 set extcommunity bandwidth num-multipaths          <<<<<<
exit
!
route-map TO_BGP_PEER_V6 permit 100
 set extcommunity bandwidth num-multipaths
exit
```

### Disable W-ECMP
If W-ECMP is `disabled`, the BGP update message contains three default path attributes `ORIGIN`/`AS_PATH`/`NEXT_HOP` when advertising network prefix 10.0.0.0/24
![Use case scenario](images/W-ECMP_disabled.png)


### Enable W-ECMP
If W-ECMP is `enabled`, the BGP `EXTENDED_COMMUNITIES` attribute is added in the update message (yellow part)
![Use case scenario](images/W-ECMP_enabled.png)


## Related DUT CLI commands

### Config
The following command can be used to enable/disable W-ECMP:
```
config bgp device-global wcmp enabled
config bgp device-global wcmp disabled
```

### Show
The following command can be used to show W-ECMP status:
```
show bgp device-global
show bgp device-global --json
```
Example:
```
admin@router:~$ show bgp device-global
TSA       WCMP
--------  -------
disabled  enabled
```
```
admin@router:~$ show bgp device-global --json
{
    "tsa": "disabled",
    "wcmp": "enabled"
}
```


## Related DUT configuration files
```
"BGP_DEVICE_GLOBAL": {
    "STATE": {
        "tsa_enabled": "false",
        "wcmp_enabled": "true"
    }
}
```


## Test cases
### Test case #1 - W-ECMP command line test
1. Enable W-ECMP and verify W-ECMP status
```
admin@router:~$ sudo config bgp device-global wcmp enabled
admin@router:~$ show bgp device-global
TSA       WCMP
--------  -------
disabled  enabled
```
2. Verify the route weight value on remote host is 25, which means W-ECMP is effect
```
admin@router:~$ ip route show 100.0.0.1
100.0.0.1 proto bgp metric 20
        nexthop via 10.10.26.1 dev Ethernet100 weight 25
        nexthop via 10.10.27.1 dev Ethernet104 weight 25
        nexthop via 10.10.28.1 dev Ethernet108 weight 25
        nexthop via 10.10.29.1 dev Ethernet112 weight 25
```
3. Disable W-ECMP and verify W-ECMP status
```
admin@router:~$ sudo config bgp device-global wcmp disabled
admin@router:~$ show bgp device-global
TSA       WCMP
--------  -------
disabled  disabled
```
4. Verify the route weight value on remote host is 1, which means W-ECMP is disabled
```
admin@router:~$ ip route show 100.0.0.1
100.0.0.1 proto bgp metric 20
        nexthop via 10.10.26.1 dev Ethernet100 weight 1
        nexthop via 10.10.27.1 dev Ethernet104 weight 1
        nexthop via 10.10.28.1 dev Ethernet108 weight 1
        nexthop via 10.10.29.1 dev Ethernet112 weight 1
```


### Test case #2 - Verify W-ECMP behavior when no link failure
1. Enable W-ECMP and verify W-ECMP status
```
admin@router:~$ sudo config bgp device-global wcmp enabled
```
2. Verify the route weight value on remote host is 25, which means W-ECMP take effective
```
admin@router:~$ ip route show 100.0.0.1
100.0.0.1 proto bgp metric 20
        nexthop via 10.10.26.1 dev Ethernet100 weight 25
        nexthop via 10.10.27.1 dev Ethernet104 weight 25
        nexthop via 10.10.28.1 dev Ethernet108 weight 25
        nexthop via 10.10.29.1 dev Ethernet112 weight 25
```
3. Sends traffic to destination 100.0.0.1
4. Verify that traffic throughput on each nexthop is the same


### Test case #3 - Verify W-ECMP behavior after link failure
1. Enable W-ECMP and verify W-ECMP status
```
admin@router:~$ sudo config bgp device-global wcmp enabled
```
2. Verify the route weight value on remote host is 25, which means W-ECMP take effective
```
admin@router:~$ ip route show 100.0.0.1
100.0.0.1 proto bgp metric 20
        nexthop via 10.10.26.1 dev Ethernet100 weight 25
        nexthop via 10.10.27.1 dev Ethernet104 weight 25
        nexthop via 10.10.28.1 dev Ethernet108 weight 25
        nexthop via 10.10.29.1 dev Ethernet112 weight 25
```
3. Shutdown one link between DUT and SPINE1
4. Verify the weight value of the route has updated after link failure
```
admin@router:~$ ip route show 100.0.0.1
100.0.0.1 proto bgp metric 20
        nexthop via 10.10.26.1 dev Ethernet100 weight 16
        nexthop via 10.10.27.1 dev Ethernet104 weight 16
        nexthop via 10.10.28.1 dev Ethernet108 weight 33
        nexthop via 10.10.29.1 dev Ethernet112 weight 33
```
5. Sends traffic to destination 100.0.0.1
6. Verify that traffic throughput on each nexthop is based on weight value of the interface
7. Recover the failed link between DUT and SPINE1
8. Verify the route weight value on remote host is 25


### Test case #4 - Verify configuration persists after warm/cold/fast reboot
1. Enable W-ECMP on DUT, verify the config take effective
2. DUT warm/cold/fast reboot
3. Verify W-ECMP configuration persist after reboot
4. Traffic test, verify the W-ECMP function still take effect


### Test case #5 - Verify interface flap
1. Enable W-ECMP on DUT
2. The interface between DUT and HOST flaps 10 times, it will trigger weight recalculation and prefix installation
3. Verify the W-ECMP function still take effect and no dump generate


### Test case #6 - Verify W-ECMP feature status flap
1. Enable/disable W-ECMP feature 10 times
2. Verify the W-ECMP function still take effect and no dump generate
