# SONiC POST support for MACSec

## Revision
| Rev |     Date    |       Author       | Change Description |      
|:---:|:-----------:|:------------------:|--------------------|
| 1 | Jul-7 2025 | Song Yuan (Arista Networks) | Initial Version |

## Table of Contents
* [Overview](#Overview)
* [Design requirements](#Design-requirements)
* [Deisgn details](#Design-details)
  * [State DB](#State-DB)
  * [Enabling POST in SAI switch init](#Enabling-POST-in-SAI-switch-init)
  * [Enabling POST in SAI MACSec init](#Enabling-POST-in-SAI-MACSec-init)
  * [Checking SAI POST status](#Checking-SAI-POST-status)
  * [Handling SAI POST failure](#Handling-SAI-POST-failure)
  * [Enabling Control Plane POST in MACSecMgr init](#Enabling-Control-Plane-POST-in-MACSecMgr-init)
  * [Enforcing FIPS compliance](#Enforcing-FIPS-compliance)

## Overview

This document describes SONiC design for Federal Information Processing Standards (FIPS) 140-3 standard compliance. Especially, the focus of the document is to trigger MACSec Pre-Operational Self-Test (POST) in SONiC and also ensure SONiC’s behavior is compliant to FIPS standard after POST.

## Design requirements

The design must meet the following requirements:
- In order to accommodate different forwarding ASIC architecture or SAI implementation, the design should support enabling POST at either switch level (during switch init) or at MACSec engine level (during MACSec engine init).
- Should enable control plane POST at the MACSec level.
- SONiC MACSec configuration must be processed only after POST passes. 
- POST failure must not affect the operation of non-MACSec ports.
- Explicit visibility must be provided if POST fails, for example, in syslog. The syslog message must include the details of the failure. For example, SAI object Id of ports that fail POST and the corresponding MACSec engine.
- SONiC CLI support to access the POST status.

## Deisgn details

The following figure depicts the data flow and SONiC components in the design. Orchagent is responsible for triggering POST via SAI calls and publishing POST status in State DB. MACSec container, precisely MACSecMgr, is enhanced to be POST aware and only process MACSec configuration after POST has passed.
The control plane POST is triggered by the MACSecMgr by querying FIPS readiness from the wpa_supplicant, which implements the MACSec control plane.

![](images/fips-post-overview.png)

### State DB

The following table is added to State DB to track MACSec POST status, including SAI and and control plane POST result/status.
```
FIPS_MACSEC_POST_TABLE

;Store MACSec POST status

key    = FIPS_MACSEC_POST_TABLE|sai
status = "switch-level-post-in-progress"    ; SAI switch level POST is in-progress.
         "macsec-level-post-in-progress"    ; SAI MACsec level POST will be triggered or in-progress.
         "pass"                             ; SAI POST passed.
         "fail"                             ; SAI POST failed. 
         "disabled"                         ; SAI POST is disabled.

key    = FIPS_MACSEC_POST_TABLE|crypto
status = "pass"                             ; Control Plane POST passed.
         "fail"                             ; Control Plane POST failed. 
timestamp = <date time>                     ; POST status update time.
```

### Enabling POST

POST is enabled only when FIPS is enabled in SONiC. FIPS can be configured via either sonic-installer, i.e., set-fips option, or config file, i.e.,/etc/sonic/fips.json. Enabling FIPS requires switch reboot, and FIPS config will be populated in FIPS_STATS table in State DB after reboot. However, there may be a latency to populate FIPS config in State DB. Therefore, checking FIPS config in State DB is reliable because Orchagent may start before FIPS config is populated. Instead, Orchagent will directly check FIPS config in the following files:
- /proc/cmdline : When FIPS is configured via sonic-installer, the result, e.g., sonic_fips=1, is written in this file.
- /etc/fips/fips_enable : If FIPS is configured via config file /etc/sonic/fips.json, /etc/fips/fips_enable is updated accordingly.

Orchagent and and MACSecMgr will trigger SAI and control plane POSTs if FIPS is enabled in either of the above files.

### Enabling POST in SAI switch init

Orchagent enables POST when creating SAI switch regardless of whether the MACSec feature is supported or enabled. This can avoid triggering POST after SAI switch creation, e.g., MACSec feature is enabled later. The below flow chart depicts the process.

![](images/fips-post-switch-init.png)

Orchagent enables POST when creating SAI switch. After SAI switch is created, Orchagent queries SAI POST capability. If POST is supported in switch init, Orchagent sets POST status to in-progress and waits for POST completion callback. Otherwise, if POST is supported only in MACSec init, Orchagent sets POST status to not-started, which informs MACSecOrch of performing POST in its initialization.

If POST is not supported in either switch or MACSec init, then SAI does not support POST. In this case, Orchagent sets POST status to fail if FIPS is enabled in SONiC.

POST is triggered in MACSecOrch initialization. Since POST is enabled via SAI MACSec create API, SAI MACSec object may be created proactively and before any MACSec port is configured.

### Checking SAI POST status

Since SAI supports POST completion callback, a callback or notification function is provided when enabling POST in SAI switch or MACSec creation. Once being invoked, the callback function sets POST status in State DB accordingly based on the POST status returned by SAI.

### Handling SAI POST failure

If SAI POST fails,  MACSecOrch reads POST status of all MACSec ports and finds out which port has failed in POST.  MACSecOrch then adds the details of the failure in syslog. The following syslog is added to report SAI POST failure.

Switch level POST failure
```
Switch MACSec POST failed
```
MACSec level POST failure
```
MACSec POST failed: oid <macsec-oid>, direction ingress|egresss
```

### Enabling POST in SAI MACSec init

POST is performed by MACSecOrch when POST is supported only in MACSec init. The following flow chart demonstrates the process.

![](images/fips-post-macsec-init.png)

### Enabling Control Plane POST in MACSecMgr init

MACSecMgr performs POST status query during process init and publishes the status in the _FIPS_MACSEC_POST_TABLE|crypto_ table. Any w. A failure will result in MACSecMgr not processing any configuration beyond this.

![](images/fips-cp-post-macsec-init.png)

### Enforcing FIPS compliance

In order to be compliant to FIPS, SONiC should process MACSec configuration only after POST passes. This is achieved by enhancing MACSecMgr, running in MACSec container, to check POST status published in State DB before processing any MACSec configuration, as shown in the flow chart below:

![](images/fips-post-compliance.png)

### CLI

The existing MACSec show CLI command _show macsec ..._ can be extended, by introducing a new argument '**--post-status**', to access the POST status from _FIPS_MACSEC_POST_TABLE_.
```
show macsec --help
Usage: show macsec [OPTIONS] [INTERFACE_NAME]

Options:
  --profile                     show all macsec profiles
  --dump-file                   store show output to a file
  --post-status                 show macsec FIPS POST(Pre-Operational Self-Test) status
  -d, --display [all|frontend]  Show internal interfaces  [default: all]
  -n, --namespace []            Namespace name or all
  -?, -h, --help                Show this message and exit.
```
Sample output
```
admin@sonic:~$ show macsec --post-status
POST Status:
===========
Module    : crypto
Status    : pass
Timestamp : 2025-10-07 11:34:11 UTC

Module    : sai
Status    : pass
Timestamp : 2025-10-07 11:34:11 UTC
```
