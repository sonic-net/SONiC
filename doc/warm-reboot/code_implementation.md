
# SWSS docker warm restart code reference

Table of Contents
=================

* [SWSS docker warm restart code reference](#swss-docker-warm-restart-code-reference)
* [Table of Contents](#table-of-contents)
* [Basic testing](#basic-testing)
  * [enable/disable swss warm upgrade](#enabledisable-swss-warm-upgrade)
  * [swss docker upgrade](#swss-docker-upgrade)
  * [Virtual switch test](#virtual-switch-test)
* [Separate syncd and swss services, and warm start configDB support](#separate-syncd-and-swss-services-and-warm-start-configdb-support)
* [swss\-flushdb script support](#swss-flushdb-script-support)
* [swss data restore](#swss-data-restore)
* [RedisClient  hmset and hgetallordered library support\.](#redisclient--hmset-and-hgetallordered-library-support)
* [libsari redis API idempotency support](#libsari-redis-api-idempotency-support)

** Note: This document is temporary. The code implementations are for reference only. Active development and testing is in progress **

# Basic testing

## enable/disable swss warm upgrade
```
root@sonic:~# config warm_restart  enable swss

root@sonic:~# show warm_restart
WARM_RESTART teamd enable false
WARM_RESTART swss neighbor_timer 5
WARM_RESTART swss enable true
WARM_RESTART system enable false
```

## swss docker upgrade

`sonic_installer upgrade_docker` command line may be used to upgrade swss docker to a new docker image without affect data plane traffic.

```
sonic_installer upgrade_docker --help
Usage: sonic_installer upgrade_docker [OPTIONS] <container_name> <tag> URL

  Upgrade docker image from local binary or URL

Options:
  -y, --yes
  --cleanup_image  Clean up old docker images
  --help           Show this message and exit.
```

Upgrade example:
```
root@sonic:~# docker images
REPOSITORY                 TAG                                   IMAGE ID            CREATED             SIZE
docker-orchagent-brcm      latest                                e322b31c1ad6        21 hours ago        296.9 MB
docker-orchagent-brcm      test_v02                              e322b31c1ad6        21 hours ago        296.9 MB
docker-fpm-quagga          latest                                afcd2237e510        2 days ago          303.4 MB
docker-fpm-quagga          warm-reboot.0-dirty-20180709.225823   afcd2237e510        2 days ago          303.4 MB
docker-teamd               latest                                54296354b8a1        2 days ago          296.6 MB
docker-teamd               warm-reboot.0-dirty-20180709.225823   54296354b8a1        2 days ago          296.6 MB
docker-syncd-brcm          latest                                293b435f8f48        2 days ago          375.9 MB
docker-syncd-brcm          warm-reboot.0-dirty-20180709.225823   293b435f8f48        2 days ago          375.9 MB
docker-snmp-sv2            latest                                5a9965d51534        2 days ago          330.6 MB
docker-snmp-sv2            warm-reboot.0-dirty-20180709.225823   5a9965d51534        2 days ago          330.6 MB
docker-lldp-sv2            latest                                7ed919240fb9        2 days ago          306 MB
docker-lldp-sv2            warm-reboot.0-dirty-20180709.225823   7ed919240fb9        2 days ago          306 MB
docker-platform-monitor    latest                                cfb9af72dc57        2 days ago          317 MB
docker-platform-monitor    warm-reboot.0-dirty-20180709.225823   cfb9af72dc57        2 days ago          317 MB
docker-database            latest                                c61388ef5d4b        2 days ago          291.8 MB
docker-database            warm-reboot.0-dirty-20180709.225823   c61388ef5d4b        2 days ago          291.8 MB
docker-dhcp-relay          latest                                cf68d734ec21        2 days ago          293.1 MB
docker-dhcp-relay          warm-reboot.0-dirty-20180709.225823   cf68d734ec21        2 days ago          293.1 MB
docker-router-advertiser   latest                                8e69dcfe794d        2 days ago          289.4 MB
docker-router-advertiser   warm-reboot.0-dirty-20180709.225823   8e69dcfe794d        2 days ago          289.4 MB
root@sonic:~# sonic_installer upgrade_docker swss test_v03  docker-orchagent-brcm_v03.gz --cleanup_image
New docker image will be installed, continue? [y/N]: y
Command: systemctl stop swss

Command: docker rm  swss
swss

Command: docker rmi  docker-orchagent-brcm:latest
Untagged: docker-orchagent-brcm:latest

Command: docker load < ./docker-orchagent-brcm_v03.gz

Command: docker tag docker-orchagent-brcm:latest docker-orchagent-brcm:test_v03

Command: systemctl restart swss

set(['e322b31c1ad6'])
Command: docker rmi -f e322b31c1ad6
Untagged: docker-orchagent-brcm:test_v02
Deleted: sha256:e322b31c1ad6e12b27a9683fc64e0ad9a63484127d06cddf277923e9d7c37419
Deleted: sha256:bcf19d6c92edd7bcf63b529f341008532b9272d30de2f206ad47728d3393cad4

Command: sleep 5

Done
root@sonic:~# docker images
REPOSITORY                 TAG                                   IMAGE ID            CREATED             SIZE
docker-orchagent-brcm      latest                                790e060184bb        21 hours ago        296.9 MB
docker-orchagent-brcm      test_v03                              790e060184bb        21 hours ago        296.9 MB
docker-fpm-quagga          latest                                afcd2237e510        2 days ago          303.4 MB
docker-fpm-quagga          warm-reboot.0-dirty-20180709.225823   afcd2237e510        2 days ago          303.4 MB
docker-teamd               latest                                54296354b8a1        2 days ago          296.6 MB
docker-teamd               warm-reboot.0-dirty-20180709.225823   54296354b8a1        2 days ago          296.6 MB
docker-syncd-brcm          latest                                293b435f8f48        2 days ago          375.9 MB
docker-syncd-brcm          warm-reboot.0-dirty-20180709.225823   293b435f8f48        2 days ago          375.9 MB
docker-snmp-sv2            latest                                5a9965d51534        2 days ago          330.6 MB
docker-snmp-sv2            warm-reboot.0-dirty-20180709.225823   5a9965d51534        2 days ago          330.6 MB
docker-lldp-sv2            latest                                7ed919240fb9        2 days ago          306 MB
docker-lldp-sv2            warm-reboot.0-dirty-20180709.225823   7ed919240fb9        2 days ago          306 MB
docker-platform-monitor    latest                                cfb9af72dc57        2 days ago          317 MB
docker-platform-monitor    warm-reboot.0-dirty-20180709.225823   cfb9af72dc57        2 days ago          317 MB
docker-database            latest                                c61388ef5d4b        2 days ago          291.8 MB
docker-database            warm-reboot.0-dirty-20180709.225823   c61388ef5d4b        2 days ago          291.8 MB
docker-dhcp-relay          latest                                cf68d734ec21        2 days ago          293.1 MB
docker-dhcp-relay          warm-reboot.0-dirty-20180709.225823   cf68d734ec21        2 days ago          293.1 MB
docker-router-advertiser   latest                                8e69dcfe794d        2 days ago          289.4 MB
docker-router-advertiser   warm-reboot.0-dirty-20180709.225823   8e69dcfe794d        2 days ago          289.4 MB

```



`systemctl restart swss`  or ` sonic_installer upgrade_docker` won't affect data plane traffic and new provisioning works well.

```
127.0.0.1:6379> keys WAR*
1) "WARM_RESTART_TABLE:portsyncd"
2) "WARM_RESTART_TABLE:neighsyncd"
3) "WARM_RESTART_TABLE:vlanmgrd"
4) "WARM_RESTART_TABLE:orchagent"

127.0.0.1:6379> hgetall "WARM_RESTART_TABLE:orchagent"
1) "restart_count"
2) "4"
127.0.0.1:6379> hgetall "WARM_RESTART_TABLE:neighsyncd"
1) "restart_count"
2) "4

```

## Virtual switch test

```
jipan@sonic-build:~/igbpatch/vs/sonic-buildimage/src/sonic-swss/tests$ sudo pytest -v --dvsname=vs --notempview
[sudo] password for jipan:
====================================================================== test session starts =======================================================================
platform linux2 -- Python 2.7.12, pytest-3.3.0, py-1.5.2, pluggy-0.6.0 -- /usr/bin/python
cachedir: .cache
rootdir: /home/jipan/igbpatch/vs/sonic-buildimage/src/sonic-swss/tests, inifile:
collected 45 items

test_acl.py::TestAcl::test_AclTableCreation PASSED                                                                                                         [  2%]
test_acl.py::TestAcl::test_AclRuleL4SrcPort PASSED                                                                                                         [  4%]
test_acl.py::TestAcl::test_AclTableDeletion PASSED                                                                                                         [  6%]
test_acl.py::TestAcl::test_V6AclTableCreation PASSED                                                                                                       [  8%]
test_acl.py::TestAcl::test_V6AclRuleIPv6Any PASSED                                                                                                         [ 11%]
test_acl.py::TestAcl::test_V6AclRuleIPv6AnyDrop PASSED                                                                                                     [ 13%]
test_acl.py::TestAcl::test_V6AclRuleIpProtocol PASSED                                                                                                      [ 15%]
test_acl.py::TestAcl::test_V6AclRuleSrcIPv6 PASSED                                                                                                         [ 17%]
test_acl.py::TestAcl::test_V6AclRuleDstIPv6 PASSED                                                                                                         [ 20%]
test_acl.py::TestAcl::test_V6AclRuleL4SrcPort PASSED                                                                                                       [ 22%]
test_acl.py::TestAcl::test_V6AclRuleL4DstPort PASSED                                                                                                       [ 24%]
test_acl.py::TestAcl::test_V6AclRuleTCPFlags PASSED                                                                                                        [ 26%]
test_acl.py::TestAcl::test_V6AclRuleL4SrcPortRange PASSED                                                                                                  [ 28%]
test_acl.py::TestAcl::test_V6AclRuleL4DstPortRange PASSED                                                                                                  [ 31%]
test_acl.py::TestAcl::test_V6AclTableDeletion PASSED                                                                                                       [ 33%]
test_acl.py::TestAcl::test_InsertAclRuleBetweenPriorities PASSED                                                                                           [ 35%]
test_acl.py::TestAcl::test_AclTableCreationOnLAGMember PASSED                                                                                              [ 37%]
test_acl.py::TestAcl::test_AclTableCreationOnLAG PASSED                                                                                                    [ 40%]
test_acl.py::TestAcl::test_AclTableCreationBeforeLAG PASSED                                                                                                [ 42%]
test_crm.py::test_CrmFdbEntry PASSED                                                                                                                       [ 44%]
test_crm.py::test_CrmIpv4Route PASSED                                                                                                                      [ 46%]
test_crm.py::test_CrmIpv6Route PASSED                                                                                                                      [ 48%]
test_crm.py::test_CrmIpv4Nexthop PASSED                                                                                                                    [ 51%]
test_crm.py::test_CrmIpv6Nexthop PASSED                                                                                                                    [ 53%]
test_crm.py::test_CrmIpv4Neighbor PASSED                                                                                                                   [ 55%]
test_crm.py::test_CrmIpv6Neighbor PASSED                                                                                                                   [ 57%]
test_crm.py::test_CrmNexthopGroup PASSED                                                                                                                   [ 60%]
test_crm.py::test_CrmNexthopGroupMember PASSED                                                                                                             [ 62%]
test_crm.py::test_CrmAcl PASSED                                                                                                                            [ 64%]
test_dirbcast.py::test_DirectedBroadcast PASSED                                                                                                            [ 66%]
test_fdb.py::test_FDBAddedAfterMemberCreated PASSED                                                                                                        [ 68%]
test_interface.py::test_InterfaceIpChange PASSED                                                                                                           [ 71%]
test_nhg.py::test_route_nhg PASSED                                                                                                                         [ 73%]
test_port.py::test_PortNotification PASSED                                                                                                                 [ 75%]
test_portchannel.py::test_PortChannel PASSED                                                                                                               [ 77%]
test_route.py::test_RouteAdd PASSED                                                                                                                        [ 80%]
test_setro.py::test_SetReadOnlyAttribute PASSED                                                                                                            [ 82%]
test_speed.py::TestSpeedSet::test_SpeedAndBufferSet PASSED                                                                                                 [ 84%]
test_vlan.py::test_VlanMemberCreation PASSED                                                                                                               [ 86%]
test_vrf.py::test_VRFOrch_Comprehensive PASSED                                                                                                             [ 88%]
test_vrf.py::test_VRFOrch PASSED                                                                                                                           [ 91%]
test_vrf.py::test_VRFOrch_Update PASSED                                                                                                                    [ 93%]
test_warm_reboot.py::test_swss_warm_restore PASSED                                                                                                         [ 95%]
test_warm_reboot.py::test_swss_port_state_syncup PASSED                                                                                                    [ 97%]
test_warm_reboot.py::test_swss_fdb_syncup_and_crm PASSED                                                                                                   [100%]

================================================================== 45 passed in 630.11 seconds ===================================================================
jipan@sonic-build:~/igbpatch/vs/sonic-buildimage/src/sonic-swss/tests$
```

# Separate syncd and swss services, and warm start configDB support
https://github.com/Azure/sonic-buildimage/compare/master...jipanyang:warm-reboot

# swss-flushdb script support
https://github.com/Azure/sonic-utilities/compare/master...jipanyang:swss-warm-restart

# swss data restore
https://github.com/Azure/sonic-swss/compare/master...jipanyang:idempotent

# RedisClient  hmset and hgetallordered library support.
https://github.com/Azure/sonic-swss-common/compare/master...jipanyang:idempotent

# libsari redis API idempotency support
https://github.com/Azure/sonic-sairedis/compare/master...jipanyang:idempotent




