# VRF feature ansible test plan <!-- omit in toc -->

<!-- TOC -->

- [overview](#overview)
  - [Scope](#scope)
  - [Testbed](#testbed)
- [Setup configuration](#setup-configuration)
  - [vrf config in t0 topo](#vrf-config-in-t0-topo)
  - [Scripts for generating configuration on SONIC](#scripts-for-generating-configuration-on-sonic)
  - [Pytest scripts to setup and run test](#pytest-scripts-to-setup-and-run-test)
  - [Setup of DUT switch](#setup-of-dut-switch)
    - [vrf configuration](#vrf-configuration)
    - [bgp vrf configuration](#bgp-vrf-configuration)
    - [acl redirect vrf configuration](#acl-redirect-vrf-configuration)
    - [teardown operation after each test case](#teardown-operation-after-each-test-case)
- [PTF Test](#ptf-test)
  - [Input files for PTF test](#input-files-for-ptf-test)
  - [Traffic validation in PTF](#traffic-validation-in-ptf)
- [Test cases](#test-cases)
  - [Test case #1 - vrf creat and bind](#test-case-1---vrf-creat-and-bind)
  - [Test case #2 - neighbor learning in vrf](#test-case-2---neighbor-learning-in-vrf)
  - [Test case #3 - route learning in vrf](#test-case-3---route-learning-in-vrf)
  - [Test case #4 - isolation among different vrfs](#test-case-4---isolation-among-different-vrfs)
  - [Test case #5 - acl redirect in vrf](#test-case-5---acl-redirect-in-vrf)
  - [Test case #6 - loopback interface](#test-case-6---loopback-interface)
  - [Test case #7 - Vrf WarmReboot](#test-case-7---vrf-warmreboot)
  - [Test case #8 - Vrf capacity](#test-case-8---vrf-capacity)
  - [Test case #9 - unbind intf from vrf](#test-case-9---unbind-intf-from-vrf)
  - [Test case #10 - remove vrf when intfs is bound to vrf](#test-case-10---remove-vrf-when-intfs-is-bound-to-vrf)
- [TODO](#todo)

<!-- /TOC -->
## overview

The purpose is to test vrf functionality on the SONIC switch DUT, closely mimic the production environment. The test will use testbed's basic configuration as default and load different vrf configurations according to the test cases.

### Scope

The test is running on real SONIC switch with testbed's basic configuration. The purpose of the test is not to test specific C/C++ class or APIs, those tests are coverd by vs test cases. The purpose is to do VRF functional test on a SONIC system. They include vrf creation/deletion, neighbor/route learning in vrf, binding/unbinding vrf to L3 intf, isolation among vrfs, acl redirection/everflow in vrf and vrf attributes function.

### Testbed

The test will run on the `t0` testbed:

## Setup configuration

### vrf config in t0 topo

![vrf-t0_topo](https://github.com/shine4chen/SONiC/blob/vrf-test-case/images/vrf_hld/vrf_t0_topo.png)

### Scripts for generating configuration on SONIC

There are some j2 template files for the vrf test configuration. They are used to generate json files and apply them on the DUT.

### Pytest scripts to setup and run test

Newly added `test_vrf.py` will be put in 'sonic-mgmt/tests/' directory.

### Setup of DUT switch

Setup of SONIC DUT will be done by SONiC CLI. During the setup process pytest will use SONiC CLI to config vrf, bind intf to vrf and add ip address to intf.

#### vrf configuration

```jason
{
    "VRF": {
        "Vrf1": {
        },
        "Vrf2": {
        }
    },
    "PORTCHANNEL_INTERFACE": {
        "PortChannel0001": {"vrf_name": "Vrf1"},
        "PortChannel0002": {"vrf_name": "Vrf1"},
        "PortChannel0003": {"vrf_name": "Vrf2"},
        "PortChannel0004": {"vrf_name": "Vrf2"},
        "PortChannel0001|10.0.0.56/31": {},
        "PortChannel0001|FC00::71/126": {},
        "PortChannel0002|10.0.0.58/31": {},
        "PortChannel0002|FC00::75/126": {},
        "PortChannel0003|10.0.0.60/31": {},
        "PortChannel0003|FC00::79/126": {},
        "PortChannel0004|10.0.0.62/31": {},
        "PortChannel0004|FC00::7D/126": {}
    },
    "VLAN_INTERFACE": {
        "Vlan1000": {"vrf_name": "Vrf1},
        "Vlan1000|192.168.0.1/21": {},
        "Vlan2000": {"vrf_name": "Vrf2},
        "Vlan2000|192.168.0.1/21": {}
    }
}
```

#### bgp vrf configuration

We modify /usr/share/sonic/templates/frr.conf.j2 to generate the frr.conf include vrf configuration and apply the frr.conf to zebra process. The new config_db.json file in T0 topo is the following.

```jason
{
    "BGP_PEER_RANGE": {
        "BGPSLBPassive": {
            "name": "BGPSLBPassive",
            "ip_range": [
                "10.255.0.0/25"
            ],
            "vrf_name": "Vrf1"
        },
        "BGPVac": {
            "name": "BGPVac",
            "ip_range": [
                "192.168.0.0/21"
            ],
            "vrf_name": "Vrf1"
        }
    },
    "BGP_NEIGHBOR": {
        "Vrf1|10.0.0.57": {
            "rrclient": "0",
            "name": "ARISTA01T1",
            "local_addr": "10.0.0.56",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf1|10.0.0.59": {
            "rrclient": "0",
            "name": "ARISTA02T1",
            "local_addr": "10.0.0.58",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf2|10.0.0.61": {
            "rrclient": "0",
            "name": "ARISTA03T1",
            "local_addr": "10.0.0.60",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf2|10.0.0.63": {
            "rrclient": "0",
            "name": "ARISTA04T1",
            "local_addr": "10.0.0.62",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf2|fc00::7a": {
            "rrclient": "0",
            "name": "ARISTA03T1",
            "local_addr": "fc00::79",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf2|fc00::7e": {
            "rrclient": "0",
            "name": "ARISTA04T1",
            "local_addr": "fc00::7d",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf1|fc00::72": {
            "rrclient": "0",
            "name": "ARISTA01T1",
            "local_addr": "fc00::71",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        },
        "Vrf1|fc00::76": {
            "rrclient": "0",
            "name": "ARISTA02T1",
            "local_addr": "fc00::75",
            "nhopself": "0",
            "admin_status": "up",
            "holdtime": "10",
            "asn": "64600",
            "keepalive": "3"
        }
    },
}
```

The frr configuration is the following.

```jason
router bgp 65100 vrf Vrf2
 bgp router-id 10.1.0.32
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 bgp graceful-restart
 bgp bestpath as-path multipath-relax
 neighbor BGPSLBPassive peer-group
 neighbor BGPSLBPassive remote-as 65432
 neighbor BGPSLBPassive passive
 neighbor BGPSLBPassive ebgp-multihop 255
 neighbor BGPVac peer-group
 neighbor BGPVac remote-as 65432
 neighbor BGPVac passive
 neighbor BGPVac ebgp-multihop 255
 neighbor 10.0.0.61 remote-as 64600
 neighbor 10.0.0.61 description ARISTA03T1
 neighbor 10.0.0.61 timers 3 10
 neighbor 10.0.0.63 remote-as 64600
 neighbor 10.0.0.63 description ARISTA04T1
 neighbor 10.0.0.63 timers 3 10
 neighbor fc00::7a remote-as 64600
 neighbor fc00::7a description ARISTA03T1
 neighbor fc00::7a timers 3 10
 neighbor fc00::7e remote-as 64600
 neighbor fc00::7e description ARISTA04T1
 neighbor fc00::7e timers 3 10
 bgp listen range 10.255.0.0/25 peer-group BGPSLBPassive
 bgp listen range 192.168.0.0/21 peer-group BGPVac
 !
 address-family ipv4 unicast
  network 10.1.0.32/32
  network 192.168.0.0/21
  neighbor 10.0.0.61 activate
  neighbor 10.0.0.61 soft-reconfiguration inbound
  neighbor 10.0.0.61 allowas-in 1
  neighbor 10.0.0.63 activate
  neighbor 10.0.0.63 soft-reconfiguration inbound
  neighbor 10.0.0.63 allowas-in 1
  neighbor BGPSLBPassive activate
  neighbor BGPSLBPassive soft-reconfiguration inbound
  neighbor BGPSLBPassive route-map FROM_BGP_SPEAKER_V4 in
  neighbor BGPSLBPassive route-map TO_BGP_SPEAKER_V4 out
  neighbor BGPVac activate
  neighbor BGPVac soft-reconfiguration inbound
  neighbor BGPVac route-map FROM_BGP_SPEAKER_V4 in
  neighbor BGPVac route-map TO_BGP_SPEAKER_V4 out
  maximum-paths 64
 exit-address-family
 !
 address-family ipv6 unicast
  network fc00:1::32/128
  network fc00:168::/117
  neighbor fc00::7a activate
  neighbor fc00::7a soft-reconfiguration inbound
  neighbor fc00::7a allowas-in 1
  neighbor fc00::7a route-map set-next-hop-global-v6 in
  neighbor fc00::7e activate
  neighbor fc00::7e soft-reconfiguration inbound
  neighbor fc00::7e allowas-in 1
  neighbor fc00::7e route-map set-next-hop-global-v6 in
  neighbor BGPSLBPassive activate
  neighbor BGPSLBPassive soft-reconfiguration inbound
  neighbor BGPVac activate
  neighbor BGPVac soft-reconfiguration inbound
  maximum-paths 64
 exit-address-family
!
router bgp 65100 vrf Vrf1
 bgp router-id 10.1.0.32
 bgp log-neighbor-changes
 no bgp default ipv4-unicast
 bgp graceful-restart
 bgp bestpath as-path multipath-relax
 neighbor BGPSLBPassive peer-group
 neighbor BGPSLBPassive remote-as 65432
 neighbor BGPSLBPassive passive
 neighbor BGPSLBPassive ebgp-multihop 255
 neighbor BGPVac peer-group
 neighbor BGPVac remote-as 65432
 neighbor BGPVac passive
 neighbor BGPVac ebgp-multihop 255
 neighbor 10.0.0.57 remote-as 64600
 neighbor 10.0.0.57 description ARISTA01T1
 neighbor 10.0.0.57 timers 3 10
 neighbor 10.0.0.59 remote-as 64600
 neighbor 10.0.0.59 description ARISTA02T1
 neighbor 10.0.0.59 timers 3 10
 neighbor fc00::72 remote-as 64600
 neighbor fc00::72 description ARISTA01T1
 neighbor fc00::72 timers 3 10
 neighbor fc00::76 remote-as 64600
 neighbor fc00::76 description ARISTA02T1
 neighbor fc00::76 timers 3 10
 bgp listen range 10.255.0.0/25 peer-group BGPSLBPassive
 bgp listen range 192.168.0.0/21 peer-group BGPVac
 !
 address-family ipv4 unicast
  network 10.1.0.32/32
  network 192.168.0.0/21
  neighbor 10.0.0.57 activate
  neighbor 10.0.0.57 soft-reconfiguration inbound
  neighbor 10.0.0.57 allowas-in 1
  neighbor 10.0.0.59 activate
  neighbor 10.0.0.59 soft-reconfiguration inbound
  neighbor 10.0.0.59 allowas-in 1
  neighbor BGPSLBPassive activate
  neighbor BGPSLBPassive soft-reconfiguration inbound
  neighbor BGPSLBPassive route-map FROM_BGP_SPEAKER_V4 in
  neighbor BGPSLBPassive route-map TO_BGP_SPEAKER_V4 out
  neighbor BGPVac activate
  neighbor BGPVac soft-reconfiguration inbound
  neighbor BGPVac route-map FROM_BGP_SPEAKER_V4 in
  neighbor BGPVac route-map TO_BGP_SPEAKER_V4 out
  maximum-paths 64
 exit-address-family
 !
 address-family ipv6 unicast
  network fc00:1::32/128
  network fc00:168::/117
  neighbor fc00::72 activate
  neighbor fc00::72 soft-reconfiguration inbound
  neighbor fc00::72 allowas-in 1
  neighbor fc00::72 route-map set-next-hop-global-v6 in
  neighbor fc00::76 activate
  neighbor fc00::76 soft-reconfiguration inbound
  neighbor fc00::76 allowas-in 1
  neighbor fc00::76 route-map set-next-hop-global-v6 in
  neighbor BGPSLBPassive activate
  neighbor BGPSLBPassive soft-reconfiguration inbound
  neighbor BGPVac activate
  neighbor BGPVac soft-reconfiguration inbound
  maximum-paths 64
 exit-address-family
!
route-map set-next-hop-global-v6 permit 10
 set ipv6 next-hop prefer-global
!
route-map ISOLATE permit 10
 set as-path prepend 65100
!
route-map TO_BGP_SPEAKER_V4 deny 10
!
route-map FROM_BGP_SPEAKER_V4 permit 10
!
route-map RM_SET_SRC6 permit 10
 set src fc00:1::32
!
route-map RM_SET_SRC permit 10
 set src 10.1.0.32
!
ip protocol bgp route-map RM_SET_SRC
!
ipv6 protocol bgp route-map RM_SET_SRC6
...
```

#### acl redirect vrf configuration

Acl redirect action supports vrf, so we need specify the outgoing interface of the nexthop explicitly, the acl redirect configuration template is as following:

```jason
{
    "ACL_TABLE": {
        "VRF_ACL_REDIRECT_V4": {
            "policy_desc": "Redirect traffic to nexthop in different vrfs",
            "type": "L3",
            "ports": ["{{ src_port }}"]
        },

        "VRF_ACL_REDIRECT_V6": {
            "policy_desc": "Redirect traffic to nexthop in different vrfs",
            "type": "L3V6",
            "ports": ["{{ src_port }}"]
        }
    },
    "ACL_RULE": {
        "VRF_ACL_REDIRECT_V4|rule1": {
            "priority": "55",
            "SRC_IP": "10.0.0.1",
            "packet_action": "redirect:{% for intf, ip in redirect_dst_ipv6s %}{{ ip ~ "|" ~ intf }}{{ "," if not loop.last else "" }}{% endfor %}"
        },
        "VRF_ACL_REDIRECT_V6|rule1": {
            "priority": "55",
            "SRC_IPV6": "2000::1",
            "packet_action": "redirect:{% for intf, ip in redirect_dst_ipv6s %}{{ ip ~ "|" ~ intf }}{{ "," if not loop.last else "" }}{% endfor %}"
        }
    }
}

```

#### teardown operation after each test case

- Restore original topo-t0 configuration

## PTF Test

### Input files for PTF test

PTF test will generate traffic between ports and make sure the traffic forwarding is expected according to the vrf configuration. Depending on the testbed topology and the existing configuration (e.g. ECMP, LAGS, etc) packets may forward to different interfaces. Therefore port connection information will be generated from the minigraph and supplied to the PTF script.

### Traffic validation in PTF

Depending on the test cases PTF will verify the packet is arrived or dropped. For vrf "src_mac" option test, PTF will analyze ip packet dst_mac after L3 forwarding through vrf and do L3 forwarding only when ip packet's dst_mac is matched with configed vrf "src_mac".

## Test cases

### Test case #1 - vrf creat and bind

#### Test objective <!-- omit in toc -->

verify vrf creat and bind intf to vrf

#### Test steps <!-- omit in toc -->

- config load vrf configuration
- verify vrf and ip configuration in kernel
- verify vrf and ip configuration in app_db

### Test case #2 - neighbor learning in vrf

#### Test objective <!-- omit in toc -->

verify arp/neighbor learning in vrf

#### Test steps <!-- omit in toc -->

- from DUT ping vms successfully
- verify neighbor entries by traffic

### Test case #3 - route learning in vrf

#### Test objective <!-- omit in toc -->

Verify v4/v6 route learning in vrf

#### Test steps <!-- omit in toc -->

- bgp load new frr.conf
- DUT exchange routes information with peer VMs
  - each vm propagates 6.4K ipv4 route and 6.4k ipv6 route to DUT.
- verify route entries by traffic(choose some routes)

### Test case #4 - isolation among different vrfs

#### Test objective <!-- omit in toc -->

The neighbor and route entries should be isolated among different vrfs.

#### Test steps <!-- omit in toc -->

- load vrf configuration and frr.conf
- both vms and DUT exchange routes via bgp
  - route prefix overlaps in different vrfs.
- verify traffic matched neighbor entry isolation in different vrf
- verify traffic matched route entry isolation in different vrf

### Test case #5 - acl redirect in vrf

#### Test objective <!-- omit in toc -->

ACL redirection can redirect packets to the nexthop with specified interface bound to the vrf.

#### Test steps <!-- omit in toc -->

- load acl_redirect configuration file
- PTF send pkts
- verify PTF ports can not receive pkt from origin L3 forward destination ports
- verify PTF ports can receive pkt from configured nexthop group member
- verify load balance between nexthop group members
- Restore configuration

### Test case #6 - loopback interface

#### Test objective <!-- omit in toc -->

User can configurate multiple loopback interfaces. Each interface can belong to different vrf.

#### Test steps <!-- omit in toc -->

- load loopback configuration file
- On ptf in different vrf ping DUT loopback interface ip address
- Verify if ping operation is successful
- use loopback interface as bgp update-source in vrf
- verify bgp session state is Established
- Restore configuration

### Test case #7 - Vrf WarmReboot

#### Test objective <!-- omit in toc -->

During system/swss warm-reboot, traffic should not be dropped.

#### Test steps <!-- omit in toc -->

- execute ptf background traffic test
- do system warm-reboot
- after system warm-reboot, stop ptf background traffic test
- verify traffic should not be dropped
- execute ptf background traffic test
- do swss warm-reboot
- after swss warm-reboot, stop ptf background traffic test
- verify traffic should not be dropped

### Test case #8 - Vrf capacity

#### Test objective <!-- omit in toc -->

Current sonic can support up to 1000 Vrf.

#### Test steps <!-- omit in toc -->

- create 1000 vlans and Vrfs using CLI
- configure Ethernet0 to 1000 vlans
- bind 1000 vlan interfaces to 1000 vrfs
- configure ip addresses on 1000 vlan interfaces
- Verify if any error log occur
- Verify 1000 vlan interfaces connection with ptf by traffic

### Test case #9 - unbind intf from vrf

#### Test objective <!-- omit in toc -->

When the interface is unbound from the vrf all neighbors and routes associated with the interface should be removed. The other interfaces still bound to vrf should not be effected.

#### Test steps <!-- omit in toc -->

- unbind some intfs from vrf
- verify neighbor and route entries removed by traffic
- verify neighbor and route entries related to  other intf should not be effected by traffic
- Restore configuration

### Test case #10 - remove vrf when intfs is bound to vrf

#### Test objective <!-- omit in toc -->

Use CLI to remove vrf when intfs is bound to the vrf, all ip addresses of the intfs belonging to the vrf should be deleted and all neighbor and route entries related to this vrf should be removed. The entries in other vrf should not be effected.

#### Test steps <!-- omit in toc -->

- load vrf configuration and frr.conf
- verify route and neigh status is okay
- remove specified vrf using CLI
- verify ip addresses of the interfaces belonging to the vrf are removed by traffic
- verify neighbor and route entries removed by traffic
- verify neighbor and route entries in other vrf existed by traffic
- Restore configuration

## TODO

- vrf table attributes 'fallback lookup' test
- vrf route leaking between VRFS
- everflow support in vrf
- application test in VRF such as ssh
