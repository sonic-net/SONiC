# RADIUS Management User Authentication

## High Level Design Document
#### Rev 0.12

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definition-abbreviation)
  * [Overview](#overview)
    * [Requirements](#requirements)
    * [Assumptions](#assumptions)
  * [Functionality](#functionality)
  * [Design](#design)
    * [PAM](#PAM)
    * [NSS](#NSS)
      * [Mapping Users](#Mapping-Users)
      * [Unconfirmed Users](#Unconfirmed-Users)
      * [User Privilege Table](#User-Privilege-Table)
    * [ConfigDB Schema](#ConfigDB-Schema)
      * [AAA Table Schema](#AAA-Table-Schema)
      * [RADIUS Table Schema](#RADIUS-Table-Schema)
      * [RADIUS_SERVER Table Schema](#RADIUS_SERVER-Table-Schema)
    * [Manageability](#Manageability)
      * [Data Models](#Data-Models)
      * [CLI](#CLI)
  * [Flow Diagrams](#flow-diagrams)
  * [Error Handling](#error-handling)
  * [Serviceability and Debug](#serviceability-and-debug)
  * [Warm Boot Support](#warm-boot-support)
  * [Scalability](#scalability)
  * [Unit Test](#unit-test)
  * [Summary of Changes](#summary-of-changes)
  * [References](#references)
    * [RFC2865](#RFC2865)
    * [RFC5607](#RFC5607)
    * [Linux-PAM](#Linux-PAM)
    * [NSS Reference](#NSS-Reference)
    * [TACACS+ Authentication](#TACPLUS-Authentication)
    * [pam_radius](#pam_radius)

# List of Tables

# Revision
| Rev | Date         |  Author            | Change Description                |
|:---:|:------------:|:------------------:|-----------------------------------|
| 0.1 | 07/12/2019   |  Arun Barboza      | Initial version                   |
| 0.2 | 07/26/2019   |  Arun Barboza      | After initial review              |
| 0.3 | 08/07/2019   |  Arun Barboza      | Added Management VRF CLI          |
| 0.4 | 08/15/2019   |  Arun Barboza      | Addressing review comments        |
| 0.5 | 10/02/2019   |  Arun Barboza      | Updates for SSH & test comments   |
| 0.6 | 10/14/2019   |  Arun Barboza      | Updates for CLI & Openconfig Model|
| 0.7 | 03/04/2020   |  Arun Barboza      | Code PR ready updates             |
| 0.8 | 04/28/2020   |  Arun Barboza      | RADIUS statistics & NAS-IP-Address|
| 0.9 | 05/04/2020   |  Arun Barboza      | Work In Progress server DNS name  |
| 0.10| 06/30/2020   |  Arun Barboza      | source-interface, and NAS-IP-Addr |
| 0.11| 08/12/2020   |  Arun Barboza      | many_to_one=n/y, Unconfirmed Users|
| 0.12| 08/25/2020   |  Arun Barboza      | Comments from 0.11 (Rev a)        |

# About this Manual
This document provides general information about the RADIUS management user
authentication feature in SONiC.

# Scope

This document describes the high level design of RADIUS management user
authentication feature in SONiC.

# Definition Abbreviation

# Overview

Remote Authentication Dial In User Service (RADIUS), is a protocol for
carrying authentication, authorization, and configuration information between
a Network Access Server (NAS) which desires to authenticate its links and
a shared Authentication Server (AS). [RFC2865](#RFC2865). RADIUS can also be
used for authenticating management access to a Network Access Server.
RADIUS can also provide accounting service.


Linux-PAM is a system of libraries that handle the authentication tasks
of applications (services) on the system. The library provides a stable
general interface (Application Programming Interface - API) that
privilege granting programs (such as login(1) and su(1)) defer to to
perform standard authentication tasks. [Linux-PAM](#Linux-PAM).


## Requirements

- Support RADIUS login authentication for SSH and console.
- Allow the source IP address for RADIUS packets to be specified.
- Support multiple RADIUS servers, with server priority configuration. If
  a RADIUS server is unreachable, the next priority server will be contacted.
  In this context, if an incorrect RADIUS passphrase(aka shared-secret) has
  been configured on the SONiC device for a RADIUS server, the resulting
  authentication failure is treated as an "unreachable"  RADIUS server, and
  the next priority server is contacted. Support configuring a maximum of
  8 servers on the SONiC device. Higher numerical priority translates to
  a higher precedence.
- Support setting up to 2 login authentication methods, including the order
  of local, and RADIUS authentication.
- Support a fail through mechanism for authentication, when configured to
  do so. If configured to do so,  when authentication with a RADIUS server
  fails, due to incorrect username/password credentials, the next RADIUS
  server will be contacted. The default configuration (fail through is not
  enabled) behavior is to immediately fail the entire authentication attempt,
  if a RADIUS server returns Access-Reject due to bad username/password.
- The root user authentication should be only done against local.
- Support obtaining the privilege level of the management user from the
  RADIUS server. Have the ability to map privilege level to SONiC device
  user information privileges (Eg: admin users who can obtain super-user
  privileges using sudo, and non-admin users who cannot, but can monitor.)
- Support using a management VRF for connecting to a RADIUS server.

## Assumptions

- After authentication, the user will be presented with a Linux Shell.
- RADIUS authenticated remote users need not have an account on the switch.
  These remote users will map to a local user based on a user profile.

# Functionality

- CLI i.e. SSH and console based users needing access to the SONiC device with
  RADIUS management user authentication.
- Applications running in docker containers needing access to PAM interface
  can instead bounce the management user authentication to the host using SSH.
  (sometimes known as "proxy" authentication)

# Design

The following figure is based of the Implementation diagram in
[TACACS+ Authentication](#TACPLUS-Authentication).

```
       +-------+  +---------+
       |  SSH  |  | Console |
       +---+---+  +----+----+
           |           |
           |   (4)     |
           |           |
+----------v-----------v---------+       +---------------------+
| AUTHENTICATION                 |       |                     |
|   +-------------------------+  |  (3)  |  +------------+     |
|   | PAM Configuration Files <--+-------+--+ AAA Config |     |
|   +-------------------------+  |       |  +------------+     |
|                                |       |                     |
|         +-------------+        |       | Host Config Daemon  |
|         |     PAM     |        |       +----------^----------+
|         |  Libraries  |        |                  |
|         +-------------+        |              (2) |
+--------------------------------+                  |
                                                    |
                                                    |
           +---------+                      +-------+--------+
           |         |        (1)           |                |
           |   CLI   +---------------------->    ConfigDB    |
           |         |                      |                |
           +---------+                      +----------------+

```


Following is the sequence of events during configuring RADIUS authentication:

1. The CLI is used to update the ConfigDB with the RADIUS and AAA configuration.
2. The Host Config Daemon(HCD) reads data from ConfigDB.
3. The HCD configures the PAM authentication files. (The AAA config module in
   the HCD is responsible for modifying PAM configuration files.)
4. All new CLI sessions (SSH, Console), now use the new PAM configurations
   to authenticate users.

Following is the sequence of events during RADIUS authenticated login to
the Console:

```
Console i/p           SONiC Device                     RADIUS Server
                  /bin/login     NSS RADIUS Plugin
----------------------------------------------------------------------

    |                 |                 |                    |
    |                 |                 |                    |
    |  Login(1)       |                 |                    |
    +---------------->|                                      |
    |                 |           Access-Request(2)          |
    |                 +------------------------------------->|
    |                 |                                      |
    |                 |           Access-Accept(3)           |
    |                 |<-------------------------------------+
    |                 |                                      |
    |             (4) |                 |                    |
    |                 | getpwnam_r()(5) |                    |
    |                 +---------------->|                    |
    |                 |                 |                    |
    |                 | user info.(6)   |                    |
    |                 |<----------------+                    |
    |                 |                 |                    |
    |  Success(7)     |                 |                    |
    |<----------------|                 |                    |
    |                 |                 |                    |

```

1. A user tries to login through the Console
2. The PAM configuration causes an Access-Request to RADIUS server.
3. RADIUS returns Access-Accept with Management-Privilege-Level (MPL)(Goto 4.),
   or Access-Reject (Authentication Failed).
4. Access-Accept: The MPL is cached.
   The user is created, if they do not exist locally.
   The group membership is updated based
   on the [User Privilege Table](#User-Privilege-Table) configuration.
5. A getpwnam_r() call is made to obtain user information.
6. Return that user information.
7. The user has authenticated successfully.

Note:
1. The above sequence has left out many details to only show important
   events, and for brevity.

2. If an application requests getpwnam_r() before any authentication is
   done, the RADIUS NSS plugin can create a local *unconfirmed* user. Once
   the user's identity and privilege are established, the user
   can be marked *confirmed*, and their group memberships updated based
   on the [User Privilege Table](#User-Privilege-Table) configuration.
   This is done prior to starting the user's session.  SSH is an example
   of such an application.

Following is the sequence of events during RADIUS authenticated login over
SSH:

```
SSH Client              SONiC Device                     RADIUS Server
                  SSH Server     NSS RADIUS Plugin
----------------------------------------------------------------------

    |                 |                 |                    |
    |                 |                 |                    |
    |  Login(1)       |                 |                    |
    +---------------->|                 |                    |
    |                 | getpwnam_r()(2) |                    |
    |                 +---------------->|                    |
    |                 |                 |                    |
    |                 | user info.(3)   |                    |
    |                 |<----------------+                    |
    |                 |                 |                    |
    |                 |                                      |
    |                 |         Access-Request(4)            |
    |                 +------------------------------------->|
    |                 |                                      |
    |                 |         Access-Accept(5)             |
    |                 |<-------------------------------------+
    |                 |                                      |
    |             (6) |                 |                    |
    |                 |                 |                    |
    |  Success(7)     |                 |                    |
    |<----------------+                 |                    |
    |                 |                 |                    |
```

1. A user tries to login through an SSH client.
2. A getpwnam_r() call is made to obtain user information.
3. If the RADIUS user is not found in the local /etc/passwd file, the NSS
   RADIUS plugin creates a local *unconfirmed* user. This user information
   is returned.
4. The PAM configuration causes an Access-Request to RADIUS server.
5. RADIUS returns Access-Accept with Management-Privilege-Level (MPL)(Goto 6.),
   or Access-Reject (Authentication Failed).
6. Access-Accept:
   The MPL is cached.
   The user is marked *confirmed*. The group membership is updated based
   on the [User Privilege Table](#User-Privilege-Table) configuration.
   The KLISH certificate is generated if it does not exist.
7. The user has authenticated successfully.

Note:
1. The above sequence has left out many details to only show important
   events, and for brevity.

2. In step 6, the group membership, and confirmation can be skipped if the
   previously cached MPL and MPL returned in Access-Accept response are
   the same.

3. In step 3, the user is not found in the local /etc/passwd file only on the
   very first authentication attempt for this user. Subsequent attempts would
   use the local user information created on the first attempt.

## PAM

The PAM to RADIUS authentication module allows any Linux device to become
a RADIUS client for authentication. [pam_radius](#pam_radius)

It supports many options in its configuration file including:

- Multiple servers, with configurable ports, shared secrets, timeouts, VRF,
  and source IP.
- The order of the servers determines the priority.
- Management-Privilege-Level attribute, which can be used to grant different
  management access level to the users. This attribute is described in
  Section 6.4 of [RFC5607](#RFC5607).

This feature enhances this support with a source patch for the following:
- CHAP authtype support.
- PEAP/TLS MSCHAPv2 support. (with the use of freeradius library)

This feature enhances this support with an external command that can be run
with support from existing PAM modules.
- Cache the Management-Privilege-Level attribute in a protected subdirectory
  under /var/cache/radius/.

This feature enhances this support with options supplied to existing PAM
modules.
- fail through mode of authentication.
- The root user authentication should be only done against local.

## NSS

RADIUS (or any PAM authenticated) users are expected to have a configuration
on the SONiC device to obtain the user information like uid, gid, home
directory, and shell (i.e. information normally returned during a
getpwnam_r() system library call). If the RADIUS user is found in the local
password file, that information is used. Normally, RADIUS is only used
for AAA, but not for nameservice. If another nameservice like LDAP is
not used, a RADIUS NSS plugin needs to be used.

The nss_radius plugin will load the configuration file /etc/radius_nss.conf.
It will also use the Management-Privilege-Level (MPL)  attribute (type 136)
information obtained from the RADIUS server during authentication, to
determine the user information that is needed to create a local user, at
the time of first login. The information of this local user is returned
during a getpwnam_r() library call.

This is similar to the [TACACS+](#TACPLUS-Authentication) NSS module in
some respects. TACACS+ protocol provides an Authorization request
that can be used to get some user attributes like privilege level. Most
TACACS+ servers allow an authorization request to precede an Authentication
request. However, the RADIUS protocol has no such request. The RADIUS
server provides the privilege level only upon successful authentication.
Because of this, for RADIUS authentication to succeed, the local user
needs to be created *unconfirmed* prior to authentication.

### Unconfirmed Users

As shown in the sequence of events during RADIUS authenticated login over
SSH, a getpwnam_r() call can precede the authentication request to the RADIUS
server. To satisfy this call, an *unconfirmed* user is created. These
users must be confirmed within a certain time interval, otherwise they
can be aged out. Confirming a user happens automatically on a successful
authentication. Once confirmed, a user is stored permanently in the
SONiC Linux local user store (/etc/passwd).

Example of an *unconfirmed* user entry in the /etc/passwd file:

```
raduser:x:1001:1001:Unconfirmed-1598315382:/home/raduser:/usr/bin/sonic-launch-shell
```

where 1598315382 is a timestamp returned by the time() system call. The unix
password on the account is locked, but other means (Eg: RADIUS password) can
be used to login.

Some of the parameters controlling *unconfirmed* users creation, and ageing
out are:

#### unconfirmed_disallow

| Value | Description                                                         |
|:-----:|:-------------------------------------------------------------------:|
| n[o]  | (Default). Allow unconfirmed users.                                 |
| y[es] | Do not allow unconfirmed users (users created before authentication)|

Eg: unconfirmed_disallow=y

If a site has a policy of not allowing *unconfirmed* user creation, this
setting can be used to requre the user to login successfully to the console, or
another application not requiring *unconfirmed* user creation, prior to allowing
SSH access for them.

#### unconfirmed_ageout

| Value | Description                                                         |
|:-----:|:-------------------------------------------------------------------:|
| secs  | (Default=600). Wait time before purging unconfirmed users.          |

Eg: unconfirmed_ageout=360

Confirming a user happens automatically on a successful authentication by
that user. Once confirmed, a user is stored permanently in the
SONiC Linux local user store (/etc/passwd).

If there are authentication attempts that are abandoned, during the
first or initial login, there would be leftover *unconfirmed* users in the
SONiC Linux local user store (/etc/passwd). These users are aged out after
some time. The actual purge of an *unconfirmed* user might occur at any time
after expiration of this time. During the deletion of an *unconfirmed* users,
all associated artifacts, for example, their home directory, are also deleted.

By default, the SSH LoginGraceTime is 120 seconds. With allowance for a few
subsequent attempts, a default of 600 seconds has been chosen. This can be
adjusted for a site as needed.

#### unconfirmed_regexp

| Value | Description                                                         |
|:-----:|:-------------------------------------------------------------------:|
| regexp| (Default=(.*: user \[priv\])\|(.*: \[accepted\])).                |
|       | The RE to match the command line of processes for which the         |
|       | creation of unconfirmed users are to be allowed.                    |

Without having a way to control which process' getpwnam_r() requests to RADIUS
NSS result in an *unconfirmed* user getting created, new users would be created
every time a non-existent user was searched. For example, ``id non-existent''
would create an *unconfirmed* user non-existent. To avoid unintentional
user creation, the RADIUS NSS only creates *unconfirmed* users when it
detects a pattern in the cmdline of the process requesting access.

Note: *user* is not an actual RE token, but it is shown only for illustration
of what match criteria is being used by default.

The default match criteria should satisfy SSH getpwnam_r() requests to RADIUS
NSS. In the future, if other applications make similar request sequences,
this setting can be adjusted.

### Mapping Users

There is an option to map all users at a privilege level to one user as
specified in the configuration file /etc/radius_nss.conf. This option is
the *many_to_one=y* option. Because of this mapping, not all features
may work, since the LOGNAME of the remote user, and the local username
will be different. (Eg: sudo)

#### many_to_one

| Value | Description                                                         |
|:-----:|:-------------------------------------------------------------------:|
| n[o]  | (Default). Create local user account on first login.                |
| y[es] | Map RADIUS users to one local user per privilege.                   |

Eg: many_to_one=y

#### many_to_one=n

This is the default and has already been described in the sequence of events.

#### many_to_one=y

Map RADIUS users option can be used if there is a requirement that
only a fixed number of users (one per privilege level) can be created
on the SONiC device.

For example, if the default [User Privilege Table](#User-Privilege-Table)
configuration is in effect, Jane's MPL was 15, and John's 1:

 - Jane would be operating as remote_user_su(gid:1000,groups:admin,sudo,docker)
 - John would be operating as remote_user(gid:999,groups:docker)

When this non-default option is in effect, and an SSH user logs in for the
first time (or with a changed MPL), the new MPL is cached, and the user
is required to login again.

### User Privilege Table

By default, user information is returned as follows for users authenticated
through RADIUS.

| MPL(privilege)| user info      | gid  | secondary grps  | shell            |
|:-------------:|:--------------:|:----:|:---------------:|:----------------:|
| 15            | remote_user_su | 1000 |admin,sudo,docker|sonic-launch-shell|
| 1-14          | remote_user    |  999 | docker          |sonic-launch-shell|


A different mapping of MPL can be configured in the /etc/radius_nss.conf,
on the switch. For example, if the following lines were added to the
configuration.

```
user_priv=15;pw_info=remote_user_su;gid=1000;group=admin,sudo,docker;shell=/usr/bin/sonic-launch-shell
user_priv=7;pw_info=netops;gid=999;group=docker;shell=/usr/bin/sonic-launch-shell
user_priv=1;pw_info=operator;gid=100;group=docker;shell=/usr/bin/sonic-launch-shell
```

the mapping of MPL would be as follows.

| MPL(privilege)| user info      | gid  | secondary grps  | shell            |
|:-------------:|:--------------:|:----:|:---------------:|:----------------:|
| 15            | remote_user_su | 1000 |admin,sudo,docker|sonic-launch-shell|
| 14-7          | netops         |  999 | docker          |sonic-launch-shell|
| 1-6           | operator       |  100 | docker          |sonic-launch-shell|

Note: The gid column is used only when mapping users (many_to_one=y).


## ConfigDB Schema

### AAA Table Schema

```
; Key
aaa_key              = "authentication"   ; AAA type
; Attributes
login                = LIST(1*32VCHAR)   ; pam modules for particular protocol,
                         ; now only support login for (local, tacacs+, radius).
                         ; Legal combinations are [ [local], [local, tacacs+ ],
                         ; [local, radius], [tacacs+, local], [radius, local] ]
failthrough          = "True" / "False"  ; failthrough mechanism for pam modules
debug                = "True" / "False"  ; debug logs for nss or pam modules
```

Note(s):
- protocol = [[tacacs+, local], [radius, local]] are the options
                                                 implementing fallback to local.
- This is an existing table specification, which has been updated for RADIUS

### RADIUS Table Schema

```
; RADIUS configuration attributes global to the system.
; Only one instance of the table exists in the system.
; Any of the global RADIUS attributes can be overwritten by the per
; server settings.
; Key
global_key           = "global"  ;  RADIUS global configuration
; Attributes
passkey              = 1*32VCHAR  ; shared secret (Valid chars: ASCII printable except SPACE, '#', and COMMA)
auth_type            = "pap" / "chap" / "mschapv2"  ; method used for
                                  ;  authenticating the communication message
src_ip               = IPAddress  ;  source IP address (IPv4 or IPv6) for the
                                  ;  outgoing UDP/IP dgram. This is being
                                  ;  obsoleted in favor of the RADIUS_SERVER
                                  ;  table src_intf attribute. If both src_ip
                                  ;  and src_intf are specified a warning log
                                  ;  can be given, and src_intf is preferred.
                                  ;  Default is determined by routing stack.
nas_ip               = IPAddress  ;  NAS-IP|IPV6-Address (Type 4|95) attribute
                                  ;  in the outgoing RADIUS PDU.
                                  ;  Default is to use an IPAddress from the
                                  ;  MGMT_INTERFACE table. See Note below.
statistics           = "True" / "False" ;  Enable statistics collection
timeout              = 1*2DIGIT  ; How many seconds to wait before deciding
                                 ; that the server has failed to respond.
retransmit           = 1*2DIGIT  ; How many times to re-send a packet, if
                                 ; there is no response.
vrf                  = vrf_name  ; Use default vrf if not specified
                                 ; (WIP) RADIUS_SERVER attribute is preferred.
src_intf             = source_interface ; Eg: eth0, Loopback0... Use the first
                                 ; IPAddress retrieved for interface for the
                                 ; outgoing UDP/IP dgram. Default is
                                 ; determined by routing stack
                                 ; (WIP) RADIUS_SERVER attribute is preferred.
```

Note: *nas_ip* : Every RADIUS PDU sent to the RADIUS server must have a
NAS-IP|IPV6-Address, or NAS-Identifier (or both) attribute. This attribute
can be configured in the RADIUS table if:
- the non-default MGMT_INTERFACE table IP address needs to be used, or
- One IP address (on a multi-homed or multi management ip device) needs to
  reliably sent.


### RADIUS_SERVER Table Schema

```
; RADIUS per server configuration in the system.
; Key
server_key           = NameOrIPAddress; RADIUS server's DNS name or IPv4|6 addr
                                      ; * DNS name is Work In Progress(WIP) *
                                      ; * in future phase                   *
; Attributes
auth_port            = 1*5DIGIT
passkey              = 1*32VCHAR  ; per server shared secret
                                  ; (Valid chars: ASCII printable except SPACE,
                                  ; '#', and COMMA)
auth_type            = "pap" / "chap" / "mschapv2"  ; method used for
                                 ; authenticating the communication message
priority             = 1*2DIGIT  ; specify RADIUS server's priority
timeout              = 1*2DIGIT
retransmit           = 1*2DIGIT
vrf                  = vrf_name  ; Use default vrf if not specified
src_intf             = source_interface ; Eg: eth0, Loopback0... Use the first
                                 ; IPAddress retrieved for interface for the
                                 ; outgoing UDP/IP dgram. Default is
                                 ; determined by routing stack
```

## Manageability

### Data Models

For configuring RADIUS, we will use [Openconfig AAA RADIUS](https://github.com/openconfig/public/blob/master/release/models/system/openconfig-aaa-radius.yang)
Only certain config related parts will be implemented. The supported config
paths are:

- /oc-sys:system/oc-aaa:aaa/oc-aaa:server-groups/oc-aaa:server-group[name=RADIUS]/oc-aaa:servers/oc-aaa:server[address=IPAddress]/config

  The container's oc-aaa:acct-port leaf will not be  supported.

  The container will be augmented to support the following additional leaves:

  - auth-type
  - priority
  - vrf
  - source-interface

  The oc-aaa:source-address will be supported only for global RADIUS conf.

  The oc-aaa:auth-port leaf will be supported only for per server conf.

- /oc-sys:system/oc-aaa:aaa/oc-aaa:server-groups/oc-aaa:server-group[name=RADIUS]/config

  The container will be augmented to support the following additional leaves
  for global RADIUS configuration:

  - source-address
  - auth-type
  - secret-key
  - timeout
  - retransmit-attempts
  - nas-ip-address         (WIP in future phase)
  - statistics             (WIP in future phase)

### CLI

The RADIUS commands will be implemented in click, and KLISH using the available
CLI framework.

For TACACS+, the existing module click commands will continue to be available.
The AAA commands are an existing click module command which will be extended
for the RADIUS Management User Authentication feature.


```
sonic# show aaa
sonic# show radius

sonic(config)# [no] radius-server source-ip <IPAddress(IPv4 or IPv6)>
sonic(config)# [no] radius-server nas-ip <IPAddress(IPv4 or IPv6)>
sonic(config)# radius-server statistics [enable|disable]
sonic(config)# [no] radius-server timeout <1 - 60>
sonic(config)# [no] radius-server retransmit <0 - 10>
sonic(config)# [no] radius-server auth-type [pap | chap | mschapv2]
sonic(config)# [no] radius-server key <TEXT>
sonic(config)# [no] radius-server host <IPAddress(IPv4 or IPv6)>        \
                                     auth-port <1 - 65535>              \
                                     timeout <1 - 60>                   \
                                     retransmit <0 - 10>                \
                                     key <TEXT>                         \
                                     auth-type [pap | chap | mschapv2]  \
                                     priority <1 - 64>                  \
                                     vrf <TEXT>                         \
                                     source-interface <iface>

sonic(config)# [no] aaa authentication login default \
    [(group {radius|tacacs+} [local]) | \
     (local [group {radius|tacacs+}])]
sonic(config)# aaa authentication failthrough [enable|disable]

```
Note: The optional "no" prefix in the above commands is a way to un-configure
the corresponding configuration. There are some examples given below.

The following table maps KLISH commands to corresponding click CLI commands.
The conformance column (conf.) identifies how the command conforms to what is
generally seen in CLI in the industry: yes = conforms, no = does not conform,
like = similar to what is seen in industry, sonic = present in SONiC only.


| KLISH CLI Command                |conf.| click CLI                          |
|:--------------------------------:|:---:|:----------------------------------:|
|                                  |     |                                    |
| show aaa                         | yes | show aaa                           |
|                                  |     |                                    |
| show radius                      | yes | show radius                        |
|                                  |     |                                    |
| [no] radius-server source-ip ... | like| config radius src_ip (see Note 1.) |
|                                  |     |                                    |
| [no] radius-server nas-ip ...    | like| config radius nas_ip               |
|                                  |     |                                    |
| radius-server statistics ...     |sonic| config radius statistics           |
|                                  |     |                                    |
| [no] radius-server retransmit ...| yes | config radius retransmit ...       |
|                                  |     |                                    |
| [no] radius-server timeout ...   | yes | config radius timeout ...          |
|                                  |     |                                    |
| [no] radius-server auth-type ... |sonic| config radius authtype ...         |
|                                  |     |                                    |
| [no] radius-server key ...       | yes | config radius passkey ...          |
|                                  |     |                                    |
| [no] radius-server host   ...    | yes | config radius {add or delete} ...  |
|                                  |     |                                    |
| aaa authentication login-method..| --- | config aaa authentication login \  |
|                                  |     |  {local or tacacs+ or radius or...}|
|                                  |     |                                    |
|         ----                     |sonic| config aaa authentication \        |
|                                  |     |  failthrough {enable or disable}   |
|                                  |     |                                    |

Note:
1. For "radius-server source-ip", generally, in the industry we see "ip radius
   source-interface" CLI. Thus, this CLI is being obsoleted in favor of
   source-interface.

Examples:

```
S5(config)# radius-server nas-ip 10.59.143.170
S5(config)# radius-server host 10.59.143.220
S5(config)# do show radius-server
---------------------------------------------------------
RADIUS Global Configuration
---------------------------------------------------------
nas-ip-addr: 10.59.143.170
timeout    : 5
auth-type  : pap
--------------------------------------------------------------------------------
HOST            AUTH-TYPE KEY       AUTH-PORT PRIORITY TIMEOUT RTSMT VRF   SI
--------------------------------------------------------------------------------
10.59.143.220   -         -         -         -        -       -     -     -
S5(config)# no radius-server nas-ip
S5(config)# do show radius-server
---------------------------------------------------------
RADIUS Global Configuration
---------------------------------------------------------
timeout    : 5
auth-type  : pap
--------------------------------------------------------------------------------
HOST            AUTH-TYPE KEY       AUTH-PORT PRIORITY TIMEOUT RTSMT VRF   SI
--------------------------------------------------------------------------------
10.59.143.220   -         -         -         -        -       -     -     -
S5(config)#
```

# Flow Diagrams

Please see the sequence diagrams in section [Design](#design)

# Error Handling

PAM and NSS modules return errors as per [Linux-PAM](#Linux-PAM), and
[NSS](#NSS-Reference) respectively.

# Serviceability and Debug

The PAM and NSS modules for RADIUS can be debugged by enabling the debug
field of the AAA|authentication redis key. (Please see ConfigDB AAA Table
Schema). The modules can also be individually traced or debugged using
the procedure given below.

The pam_radius module can be debugged using the "debug" option specification
on the rule which causes inclusion of the module in the authentication stack.

Eg:

auth    [success=2 new_authtok_reqd=done default=ignore]  \
    pam_radius_auth.so conf=/etc/pam_radius_auth.d/10.75.133.49:1812.conf \
    privilege_level protocol=pap try_first_pass debug

The radius_nss module can be debugged using the "debug=on" or "debug=trace"
option in the /etc/radius_nss.conf file


# Warm Boot Support

N/A

# Scalability

A maximum of 8 RADIUS servers can be configured.

# Unit Test

- config aaa authentication login local radius:
```
    Verify RADIUS user is authenticated
    Verify invalid user is rejected
    For a user appearing in both local, and RADIUS verify they are
      authenticated locally.
```

- config aaa authentication login radius local:
```
    Verify RADIUS user is authenticated
    Verify invalid user is rejected
    Verify RADIUS user has priority over local user
    Verify root is authenticated locally
        (note: default root login is disabled locally)
```

- config aaa authentication login radius:
```
    Verify RADIUS user is authenticated
    Verify invalid user is rejected
    Verify root is authenticated locally
        (note: default root login is disabled locally)
```

- config aaa authentication login local radius,
  config aaa authentication failthrough enable,
  Create user:pass on server, and user:localpass locally:
```
    Verify that user:pass can login.
```

- config aaa authentication login radius,
  config aaa authentication failthrough enable,
  Create user1:pass1 on server1, and user2:pass2 on server2 (server1, and
  server2 are configured in that priority order):
```
    Verify that user2 is allowed to login with correct password.
```

# Summary of Changes

## Version 0.10 to 0.11

    * Creation of Unconfirmed (aka anonymous identity) users is now default.
    * Dropped the "many_to_one=a", since this is the default now.
    * The shell for users is adjusted to be /usr/bin/sonic-launch-shell
    * Dropped the "uid", "dir" User Privilege Table attributes to defer
      to System assigned values.
    * Added following configs to radius_nss.conf.j2
      + unconfirmed_disallow (For determining whether unconfirmed users
        should be added)
      + unconfirmed_ageout (For determining when an unconfirmed user
        can be dropped)
      + unconfirmed_regexp (For determining when an unconfirmed user
        can be created)

    * Adjusted the many_to_one=y option to be more in line with TACACS+
      implementation.
      + If the mapped user (i.e. the range, not the domain) is missing,
        create them.

    * Handle Certificate generation, if required, after authentication.
    * If the user's privilege level changes (or is initialized):
      + many_to_one=n: (default)
            adjust their group memberships
      + many_to_one=y:
            Cache the new MPL, and have them login again.

# References

## RFC2865

https://tools.ietf.org/html/rfc2865

## RFC5607

https://tools.ietf.org/html/rfc5607

## Linux PAM

http://man7.org/linux/man-pages/man3/pam.3.html

## NSS Reference

http://man7.org/linux/man-pages/man5/nsswitch.conf.5.html

## TACPLUS Authentication

https://github.com/Azure/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md

## pam_radius

https://github.com/FreeRADIUS/pam_radius


