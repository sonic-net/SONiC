# VRF feature ansible test plan

<!-- TOC -->

- [VRF feature ansible test plan](#VRF-feature-ansible-test-plan)
  - [overview](#overview)
    - [Scope](#Scope)
    - [Testbed](#Testbed)
  - [Setup configuration](#Setup-configuration)
    - [vrf config in t0 topo](#vrf-config-in-t0-topo)
    - [Scripts for generating configuration on SONIC](#Scripts-for-generating-configuration-on-SONIC)
    - [Pytest scripts to setup and run test](#Pytest-scripts-to-setup-and-run-test)
    - [Setup of DUT switch](#Setup-of-DUT-switch)
      - [vrf configuration](#vrf-configuration)
      - [bgp vrf configuration](#bgp-vrf-configuration)
      - [acl vrf configuration](#acl-vrf-configuration)
      - [teardown operation after each test case](#teardown-operation-after-each-test-case)
  - [PTF Test](#PTF-Test)
    - [Input files for PTF test](#Input-files-for-PTF-test)
    - [Traffic validation in PTF](#Traffic-validation-in-PTF)
  - [Test cases](#Test-cases)
    - [Test case #1 - vrf creat and bind](#Test-case-1---vrf-creat-and-bind)
      - [Test objective](#Test-objective)
      - [Test steps](#Test-steps)
    - [Test case #2 - neighbor learning in vrf](#Test-case-2---neighbor-learning-in-vrf)
      - [Test objective](#Test-objective-1)
      - [Test steps](#Test-steps-1)
    - [Test case #3 - route learning in vrf](#Test-case-3---route-learning-in-vrf)
      - [Test objective](#Test-objective-2)
      - [Test steps](#Test-steps-2)
    - [Test case #4 - unbind intf from vrf](#Test-case-4---unbind-intf-from-vrf)
      - [Test objective](#Test-objective-3)
      - [Test steps](#Test-steps-3)
    - [Test case #5 - remove vrf when intfs is bound to vrf](#Test-case-5---remove-vrf-when-intfs-is-bound-to-vrf)
      - [Test objective](#Test-objective-4)
      - [Test steps](#Test-steps-4)
    - [Test case #6 - isolation among different vrfs](#Test-case-6---isolation-among-different-vrfs)
      - [Test objective](#Test-objective-5)
      - [Test steps](#Test-steps-5)
    - [Test case #7 - vrf table attributes 'src_mac' test](#Test-case-7---vrf-table-attributes-srcmac-test)
      - [Test objective](#Test-objective-6)
      - [Test steps](#Test-steps-6)
    - [Test case #8 - vrf table attributes 'ttl_action' test](#Test-case-8---vrf-table-attributes-ttlaction-test)
      - [Test objective](#Test-objective-7)
      - [Test steps](#Test-steps-7)
    - [Test case #9 - vrf table attributes 'ip_opt_action' test](#Test-case-9---vrf-table-attributes-ipoptaction-test)
      - [Test objective](#Test-objective-8)
      - [Test steps](#Test-steps-8)
    - [Test case #10 - vrf table attributes 'v4/v6' test](#Test-case-10---vrf-table-attributes-v4v6-test)
      - [Test objective](#Test-objective-9)
      - [Test steps](#Test-steps-9)
    - [Test case #11 - acl redirect in vrf](#Test-case-11---acl-redirect-in-vrf)
      - [Test objective](#Test-objective-10)
      - [Test steps](#Test-steps-10)
    - [Test case #12 - everflow in vrf](#Test-case-12---everflow-in-vrf)
      - [Test objective](#Test-objective-11)
      - [Test steps](#Test-steps-11)
    - [Test case #13 - loopback interface](#Test-case-13---loopback-interface)
      - [Test objective](#Test-objective-12)
      - [Test steps](#Test-steps-12)
    - [Test case #14 - Vrf capacity](#Test-case-14---Vrf-capacity)
      - [Test objective](#Test-objective-13)
      - [Test steps](#Test-steps-13)
  - [TODO](#TODO)

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

Setup of SONIC DUT will be done by Ansible script. During the setup process Ansible will copy JSON file containing configuration for vrf to directory `/home/admin/vrf_cfg/` on the DUT. Config load utility will be used to push configuration to the SONiC Config-DB.

#### vrf configuration

```jason
{
    "VRF": {
        "Vrf1": {
            "src_mac": "00:10:94:00:00:01",
            "ttl_action": "drop",
            "ip_opt_action": "drop"
        },
        "Vrf2": {
            "ttl_action": "forward",
            "ip_opt_action": "forward"
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
        "Vlan1000|192.168.0.1/21": {}
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
! set static default route to mgmt gateway as a backup to learned default
ip route 0.0.0.0/0 10.251.0.1 200
! Set ip source to loopback for bgp learned routes
route-map RM_SET_SRC permit 10
    set src 10.1.0.32
!
route-map RM_SET_SRC6 permit 10
    set src fc00:1::32
!
ip protocol bgp route-map RM_SET_SRC
!
ipv6 protocol bgp route-map RM_SET_SRC6
!
!
!
! bgp multiple-instance
!
route-map FROM_BGP_SPEAKER_V4 permit 10
!
route-map TO_BGP_SPEAKER_V4 deny 10
!
router bgp 65100 vrf Vrf2
  bgp log-neighbor-changes
  bgp bestpath as-path multipath-relax
  no bgp default ipv4-unicast
  bgp graceful-restart
  neighbor 10.0.0.61 remote-as 64600
  neighbor 10.0.0.61 description ARISTA03T1
  neighbor 10.0.0.61 timers 3 10
  address-family ipv4
    neighbor 10.0.0.61 allowas-in 1
    neighbor 10.0.0.61 activate
    neighbor 10.0.0.61 soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
  neighbor 10.0.0.63 remote-as 64600
  neighbor 10.0.0.63 description ARISTA04T1
  neighbor 10.0.0.63 timers 3 10
  address-family ipv4
    neighbor 10.0.0.63 allowas-in 1
    neighbor 10.0.0.63 activate
    neighbor 10.0.0.63 soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
  neighbor fc00::7a remote-as 64600
  neighbor fc00::7a description ARISTA03T1
  neighbor fc00::7a timers 3 10
  address-family ipv6
    neighbor fc00::7a allowas-in 1
    neighbor fc00::7a activate
    neighbor fc00::7a soft-reconfiguration inbound
    neighbor fc00::7a route-map set-next-hop-global-v6 in
    maximum-paths 64
  exit-address-family
  neighbor fc00::7e remote-as 64600
  neighbor fc00::7e description ARISTA04T1
  neighbor fc00::7e timers 3 10
  address-family ipv6
    neighbor fc00::7e allowas-in 1
    neighbor fc00::7e activate
    neighbor fc00::7e soft-reconfiguration inbound
    neighbor fc00::7e route-map set-next-hop-global-v6 in
    maximum-paths 64
  exit-address-family
!
router bgp 65100 vrf Vrf1
  bgp log-neighbor-changes
  bgp bestpath as-path multipath-relax
  no bgp default ipv4-unicast
  bgp graceful-restart
  bgp router-id 10.1.0.32
  network 10.1.0.32/32
  address-family ipv6
    network fc00:1::32/128
  exit-address-family
  network 192.168.0.1/21
  neighbor 10.0.0.59 remote-as 64600
  neighbor 10.0.0.59 description ARISTA02T1
  neighbor 10.0.0.59 timers 3 10
  address-family ipv4
    neighbor 10.0.0.59 allowas-in 1
    neighbor 10.0.0.59 activate
    neighbor 10.0.0.59 soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
  neighbor fc00::76 remote-as 64600
  neighbor fc00::76 description ARISTA02T1
  neighbor fc00::76 timers 3 10
  address-family ipv6
    neighbor fc00::76 allowas-in 1
    neighbor fc00::76 activate
    neighbor fc00::76 soft-reconfiguration inbound
    neighbor fc00::76 route-map set-next-hop-global-v6 in
    maximum-paths 64
  exit-address-family
  neighbor fc00::72 remote-as 64600
  neighbor fc00::72 description ARISTA01T1
  neighbor fc00::72 timers 3 10
  address-family ipv6
    neighbor fc00::72 allowas-in 1
    neighbor fc00::72 activate
    neighbor fc00::72 soft-reconfiguration inbound
    neighbor fc00::72 route-map set-next-hop-global-v6 in
    maximum-paths 64
  exit-address-family
  neighbor 10.0.0.57 remote-as 64600
  neighbor 10.0.0.57 description ARISTA01T1
  neighbor 10.0.0.57 timers 3 10
  address-family ipv4
    neighbor 10.0.0.57 allowas-in 1
    neighbor 10.0.0.57 activate
    neighbor 10.0.0.57 soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
  neighbor BGPVac peer-group
  neighbor BGPVac passive
  neighbor BGPVac remote-as 65432
  neighbor BGPVac ebgp-multihop 255
  bgp listen range 192.168.0.0/21 peer-group BGPVac
  address-family ipv4
    neighbor BGPVac activate
    neighbor BGPVac soft-reconfiguration inbound
    neighbor BGPVac route-map FROM_BGP_SPEAKER_V4 in
    neighbor BGPVac route-map TO_BGP_SPEAKER_V4 out
    maximum-paths 64
  exit-address-family
  address-family ipv6
    neighbor BGPVac activate
    neighbor BGPVac soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
  neighbor BGPSLBPassive peer-group
  neighbor BGPSLBPassive passive
  neighbor BGPSLBPassive remote-as 65432
  neighbor BGPSLBPassive ebgp-multihop 255
  bgp listen range 10.255.0.0/25 peer-group BGPSLBPassive
  address-family ipv4
    neighbor BGPSLBPassive activate
    neighbor BGPSLBPassive soft-reconfiguration inbound
    neighbor BGPSLBPassive route-map FROM_BGP_SPEAKER_V4 in
    neighbor BGPSLBPassive route-map TO_BGP_SPEAKER_V4 out
    maximum-paths 64
  exit-address-family
  address-family ipv6
    neighbor BGPSLBPassive activate
    neighbor BGPSLBPassive soft-reconfiguration inbound
    maximum-paths 64
  exit-address-family
!
route-map ISOLATE permit 10
set as-path prepend 65100
!
route-map set-next-hop-global-v6 permit 10
set ipv6 next-hop prefer-global
!
...
```

#### acl vrf configuration

Acl redirect action supports vrf, so we need specify the outgoing interface of the nexthop explicitly, the acl redirect configuration file is as following:

```jason
{
    "ACL_TABLE": {
        "table1": {
            "policy_desc": "ACL REDIRECT",
            "type": "L3",
            "ports": ["Ethernet0"],
            "stage": "INGRESS"
        }
    },
    "ACL_RULE": {
        "table1|rule1": {
            "PRIORITY": "100",
            "L4_SRC_PORT": "100",
            "PACKET_ACTION": "REDIRECT:10.0.0.57|PortChannel0001,10.0.0.61|PortChannel0003"
        }
    }
}
```

#### teardown operation after each test case

- Restore original configuration by config reload utility

## PTF Test

### Input files for PTF test

PTF test will generate traffic between ports and make sure the traffic forwarding is expected according to the vrf configuration. Depending on the testbed topology and the existing configuration (e.g. ECMP, LAGS, etc) packets may forward to different interfaces. Therefore port connection information will be generated from the minigraph and supplied to the PTF script.

### Traffic validation in PTF

Depending on the test cases PTF will verify the packet is arrived or dropped. For vrf "src_mac" option test, PTF will analyze ip packet dst_mac after L3 forwarding through vrf and do L3 forwarding only when ip packet's dst_mac is matched with configed vrf "src_mac".

## Test cases

### Test case #1 - vrf creat and bind

#### Test objective

verify vrf creat and bind intf to vrf

#### Test steps

- config load vrf configuration
- verify vrf and ip configuration in kernel
- verify vrf and ip configuration in app_db

### Test case #2 - neighbor learning in vrf

#### Test objective

verify arp/neighbor learning in vrf

#### Test steps

- from DUT ping vms successfully
- verify neighbor entries by traffic

### Test case #3 - route learning in vrf

#### Test objective

Verify v4/v6 route learning in vrf

#### Test steps

- bgp load new frr.conf
- DUT exchange routes information with peer VMs
  - each vm propagates 6.4K ipv4 route and 6.4k ipv6 route to DUT.
- verify route entries by traffic(choose some routes)

### Test case #4 - unbind intf from vrf

#### Test objective

When the interface is unbound from the vrf all neighbors and routes associated with the interface should be removed. The other interfaces still bound to vrf should not be effected.

#### Test steps

- unbind some intfs from vrf
- verify neighbor and route entries removed by traffic
- verify neighbor and route entries related to  other intf should not be effected by traffic
- Restore configuration

### Test case #5 - remove vrf when intfs is bound to vrf

#### Test objective

Use CLI to remove vrf when intfs is bound to the vrf, all ip addresses of the intfs belonging to the vrf should be deleted and all neighbor and route entries related to this vrf should be removed. The entries in other vrf should not be effected.

#### Test steps

- load vrf configuration and frr.conf
- verify route and neigh status is okay
- remove specified vrf using CLI
- verify ip addresses of the interfaces belonging to the vrf are removed by traffic
- verify neighbor and route entries removed by traffic
- verify neighbor and route entries in other vrf existed by traffic
- Restore configuration

### Test case #6 - isolation among different vrfs

#### Test objective

The neighbor and route entries should be isolated among different vrfs.

#### Test steps

- load vrf configuration and frr.conf
- from DUT ping vms successfully
- both vms and DUT exchange routes via bgp
  - route prefix overlaps in different vrfs.
- verify vms can learn route from DUT
- verify traffic matched neighbor entry isolation in different vrf
- verify traffic matched route entry isolation in different vrf

### Test case #7 - vrf table attributes 'src_mac' test

#### Test objective

In ingress stage, the ip packet whose dst_mac matches the vrf configured src_mac can be L3 forwarded. If not match, the packet will be L2 fowarded. In egress stage ip packet src_mac must be modified to the vrf configured src_mac. The vrf without src_mac attribute will use the default router mac.

#### Test steps

- verify packet whose dst_mac matched the 'src_mac' of Vrf1 will be L3 forwarded in Vrf1
- verify packet whose dst_mac don't match the 'src_mac' of Vrf1 will be L2 forwarded in Vrf1. In our environment these packets will be droped.
- verify in Vrf1 L3 forwarded packets' src_mac are modified to configured 'src_mac'
- verify packet whose dst_mac matched default router mac will be L3 forwarded in Vrf2
- verify in Vrf2 L3 forwarded packets src_mac should be default router mac

### Test case #8 - vrf table attributes 'ttl_action' test

#### Test objective

Action for Packets with TTL 0 or 1. When set to 'drop',the packets with TTL 0 or 1 will be dropped.This attribute is vrf based, different vrf may have different 'ttl_action'.

#### Test steps

- verify packets with TTL 0 or 1 will be dropped in Vrf1
- verify packets with TTL more than 1 will be forwarded in Vrf1
- verify packets with TTL 0 or 1 will be fowarded in Vrf2

### Test case #9 - vrf table attributes 'ip_opt_action' test

#### Test objective

Action for Packets with IP options. When set to 'drop',the packets with IP options will be dropped. This attribute is vrf based, different vrf may have different 'ip_opt_action'.

#### Test steps

- verify packets with IP options will be dropped in Vrf1
- verify packets without IP options will be forwarded in Vrf1
- verify packets with IP options will be fowarded in Vrf2

### Test case #10 - vrf table attributes 'v4/v6' test

#### Test objective

When 'v4' atrribute is setted to 'false', it will prevent ipv4 L3 forwarding, ipv6 L3 fowarding is not effected. This attribute is vrf based, different vrf may have different 'v4/v6' state.

#### Test steps

- set 'v4' state to 'false' in Vrf1
- verify ipv4 L3 forwarding is prevented in Vrf1
- verify ipv6 L3 forwarding is not effected in Vrf1
- verify ipv4 L3 forwarding is not effected in Vrf2
- set 'v6' state to 'false' in Vrf1
- verify ipv6 L3 forwarding is prevented in Vrf1
- verify ipv6 L3 forwarding is not effected in Vrf2
- Restore configuration

### Test case #11 - acl redirect in vrf

#### Test objective

ACL redirection can redirect packets to the nexthop with specified interface bound to the vrf.

#### Test steps

- load acl_redirect configuration file
- PTF sends pkts with incremental UDP dport,sport is 100
- verify PTF ports can receive pkt from PortChannel0001 and PortChannel0002
- Restore configuration

### Test case #12 - everflow in vrf

#### Test objective

Everflow will mirror traffic to destination found in specific VRF. When route nexthop change, traffic will be mirrored to valid ports.

#### Test steps

- load everflow_vrf configuration
- send packets which match everflow rules
- verify traffic in specific VRF
- route change in specific VRF
- verify traffic in specific VRF

### Test case #13 - loopback interface

#### Test objective

User can configurate multiple loopback interfaces. Each interface can belong to different vrf.

#### Test steps

- load loopback configuration file
- On Vms in different vrf ping DUT loopback interface ip address
- Verify if ping operation is successful
- Restore configuration

### Test case #14 - Vrf capacity

#### Test objective

Current sonic can support up to 1000 Vrf.

#### Test steps

- create 1000 vlans and Vrfs using CLI
- configure Ethernet0 to 1000 vlans
- bind 1000 vlan interfaces to 1000 vrfs
- configure ip addresses on 1000 vlan interfaces
- Verify if any error log occur
- Verify 1000 vlan interfaces connection with vm by traffic

## TODO

- vrf table attributes 'l3_mc_action' test
- vrf table attributes 'fallback lookup' test
- vrf route leaking between VRFS
- application test in VRF such as ssh
