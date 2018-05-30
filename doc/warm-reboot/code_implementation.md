
# SWSS docker warm restart code reference

Table of Contents
=================

* [Basic testing](#basic-testing)
* [Separate syncd and swss services, and warm start configDB support](#separate-syncd-and-swss-services-and-warm-start-configdb-support)
* [swss\-flushdb script support](#swss-flushdb-script-support)
* [swss data restore](#swss-data-restore)
* [RedisClient  hmset and hgetallordered library support\.](#redisclient--hmset-and-hgetallordered-library-support)
* [libsari redis API idempotency support](#libsari-redis-api-idempotency-support)
* [Simple warm\_restart enable/disable/show CLI with configDB support](#simple-warm_restart-enabledisableshow-cli-with-configdb-support)




** Note: This document is temporary. The code implementations are for reference only. Active development and testing is in progress **

# Basic testing
After system restart or systemctl restart syncd:

`systemctl restart swss`  won't affect data plane traffic and new provisioning works well.

```
127.0.0.1:6379> keys WAR*
1) "WARM_START_TABLE:vlanmgrd"
2) "WARM_START_TABLE:portsyncd"
3) "WARM_START_TABLE:orchagent"

127.0.0.1:6379> hgetall "WARM_START_TABLE:orchagent"
1) "restart_count"
2) "4"

127.0.0.1:6379> hgetall "WARM_START_TABLE:portsyncd"
1) "restart_count"
2) "4"

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

# Simple warm_restart enable/disable/show CLI with configDB support

https://github.com/Azure/sonic-buildimage/compare/master...jipanyang:warm-reboot

```
root@sonic:~# config warm_restart enable swss

root@sonic:~# show warm_restart
WARM_RESTART teamd enable false
WARM_RESTART swss enable true
WARM_RESTART system enable false

```



