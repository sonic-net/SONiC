Table of Contents
=================

* [What are the development phases and scope for Warm reboot](#what-are-the-development-phases-and-scope-for-warm-reboot)
* [What are the major steps to perform docker warm upgrade?](#what-are-the-major-steps-to-perform-docker-warm-upgrade)
* [Is there kernel warm reboot cmd line like fast\-reboot?](#is-there-kernel-warm-reboot-cmd-line-like-fast-reboot)
* [SAI API change use cases](#sai-api-change-use-cases)
* [OID restore approaches: View comparison and idempotent libsairedis API](#oid-restore-approaches-view-comparison-and-idempotent-libsairedis-api)
  * [Idempotent libsairedis API](#idempotent-libsairedis-api)
    * [Design doc:](#design-doc)
    * [Draft code changes:](#draft-code-changes)
    * [Current status:](#current-status)
  * [syncd view comparison:](#syncd-view-comparison)
    * [Code change:](#code-change)
    * [Design doc:](#design-doc-1)
    * [Current status:](#current-status-1)
* [What is the requirement on libsai as to planned/unplanned warm restart?](#what-is-the-requirement-on-libsai-as-to-plannedunplanned-warm-restart)
* [How to determine the success/failure of warm restart?](#how-to-determine-the-successfailure-of-warm-restart)



# What are the development phases and scope for Warm reboot

`Phase 1`:  docker warm restart:  swss, BGP

`Phase 2`:  docker warm restart:  teamd, syncd(including libsai/SDK).

`Phase 3`:  system warm reboot: all remain parts: DB data save and restore, Linux environment graceful restore and etc.


# What are the major steps to perform docker warm upgrade?

1. Config

Enable warm restart for specific docker and provide timer value if default value doesn't fit your environment.

Ex.
```
root@sonic:/home/admin# config warm_restart enable swss

root@sonic:/home/admin# show warm_restart config
name enable timer_name timer_duration
------ -------- ------------ ----------------
swss true NULL NULL
```

Or enable warm restart at system level, it implicitly enable docker level warm restart.

Ex.
```
root@sonic:~# config warm_restart enable
root@sonic:~# show warm_restart config
name    enable    timer_name    timer_duration
------  --------  ------------  ----------------
swss    true      NULL          NULL
system  true      NULL          NULL
```

2.  Do docker upgrade

upgrade_docker command is designed to facilitate this task.
Mandatory parameters: docker name,   tag for new docker image,   docker image path.

Ex.
```
      sonic_installer upgrade_docker --cleanup_image swss swss_test_02 ./docker-orchagent-brcm_test_02.gz
```

More options are to be provided like whether to enforce stringent state check and validation.

3. Docker warm restart

For simple docker warm restart,  after the config step, just use systemd command.
Ex.
```
  systemctl restart swss
```

# Is there kernel warm reboot cmd line like fast-reboot?
Yes,  new system level warm reboot command will be provided.  Since system warm reboot involves more state save and restore work,  more options are needed compared with fast-reboot.


# SAI API change use cases
In general,  it is expected  all data plane service affecting SAI api shall be backward compatible.  If we see such cases that backward compatibility is broken  in the future,  they'll be handled case by case.

The similar requirement for SONiC as to libsai redis interface, though likely it may have more freedom of version changes.



# OID restore approaches: View comparison and idempotent libsairedis API
Both approaches have been under development and testing. Current status:

## Idempotent libsairedis API
### Design doc:
[SONiC libsairedis API idempotence support](https://github.com/Azure/SONiC/blob/master/doc/warm-reboot/sai_redis_api_idempotence.md)
### Draft code changes:
[libsairedis code changes](https://github.com/Azure/sonic-sairedis/compare/master...jipanyang:idempotent)
### Current status:
A series of virtual switch test cases  have been implemented, and end to end integration testing as to swss docker warm restart/upgrade have been done based on this solution.

No official review for the code change yet, also some restructuring is needed to make it more independent of existing libsairedis code file and flow.

It is desired to be able to switch the feature on and off with one simple command.

## syncd view comparison:

### Code change:
This file contains major part of the implementation (not complete):

[syncd_applyview.cpp](https://github.com/Azure/sonic-sairedis/blob/d54977f297301f972e2839d526d8130a5f66e893/syncd/syncd_applyview.cpp)
### Design doc:
      Not available yet.

### Current status:
Major code changes are already in sycd repo, but not being actively used in SONiC code logical flow, nor have been verified in production environment as of today.

There are unit test cases available at syncd docker only, but integration test is to be done.

# What is the requirement on libsai as to planned/unplanned warm restart?
Only planned warm restart is mandatory. SONiC will issue explicit request to libsai/SDK for warm restart.

# How to determine the success/failure of warm restart?
Warm restart is usually performed in two steps: state restore and state sync up.
For start restore,  based on configuration, a series of state consistency check and validation could be done to ensure application has reached the desired state.

State sync up is a little tricky, since application is trying to get synchronized with lastest state which is not deterministic. Current idea is to have an application specific timer to guard this process. Once timer expires, the sync up processing is treat as done and successfull. Each application should apply its own internal speicific check.


