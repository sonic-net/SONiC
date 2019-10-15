# RADIUS Management User Authentication

## High Level Design Document
#### Rev 0.6

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
  * [Flow Diagrams](#flow-diagrams)
  * [Error Handling](#error-handling)
  * [Serviceability and Debug](#serviceability-and-debug)
  * [Warm Boot Support](#warm-boot-support)
  * [Scalability](#scalability)
  * [Unit Test](#unit-test)
  * [References](#references)
    * [RFC2865](#RFC2865)
    * [RFC5607](#RFC5607)
    * [Linux-PAM](#Linux-PAM)
    * [NSS Reference](#NSS-Reference)
    * [TACACS+ Authentication](#TACPLUS-Authentication)
    * [pam_radius](#pam_radius)
  * [Internal Design Information](#internal-design-information)

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
5. A getpwnam_r() call is made to obtain user information.
6. If the RADIUS user is not found in the local /etc/passwd file, the NSS
   RADIUS plugin uses the cached MPL information to return user information.
7. The user has authenticated successfully.

Note:
1. If an application requests getpwnam_r() before any authentication is
   done, the RADIUS NSS plugin can be configured to return a least privileged
   (MPL 1) temporary user info. On subsequent sessions, the user info will
   be returned per the cached MPL. SSH is an example of such an application.
   Alternatively, the user can be asked to login to console for the first
   time to cache the MPL. Subsequent sessions will now use the cached MPL.

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
    |             (4) |                 |                    |
    |                 |                 |                    |
    |                 |                                      |
    |                 |         PAM Auth Request(5)          |
    |                 +------------------------------------->|
    |                 |                                      |
    |                 |         PAM Auth Success(6)          |
    |                 |<-------------------------------------+
    |                 |                                      |
    |                 |                 |                    |
    |  Success(7)     |                 |                    |
    |<----------------+                 |                    |
    |                 |                 |                    |
```

1. A user tries to login through a SSH client.
2. A getpwnam_r() call is made to obtain user information.
3. If the RADIUS user is not found in the local /etc/passwd file, the NSS
   RADIUS plugin uses the cached MPL information to return user information.
   If no MPL is available, and the many_to_one=a is configured, a least
   privileged (MPL 1) temporary user info is returned. Otherwise, the
   login fails.
4. The PAM configuration causes a Access-Request to RADIUS server.
5. RADIUS returns Access-Accept with Management-Privilege-Level (MPL)(Goto 6.),
   or Access-Reject (Authentication Failed).
6. Access-Accept: The MPL is cached.
7. The user has authenticated successfully.

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
  under /var/run/radius/.

This feature enhances this support with options supplied to existing PAM
modules.
- fail through mode of authentication.
- The root user authentication should be only done against local.

## NSS

RADIUS (or any PAM authenticated) users are expected to have a configuration
on the SONiC device to obtain the user information like uid, gid , home
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

There is an option to map all users at a privilege level to one user as
specified in the configuration file /etc/radius_nss.conf. This option is
the many_to_one=y option. When this option is in effect, no local user is
created at the time of login. Because of the mapping, not all features
may apply, since the LOGNAME of the user, and the mapped uid may not match.

For SSH login, Note 1. under sequence of events during RADIUS authenticated
login will apply. The configuration option for this Note 1. to apply
is many_to_one=a.


### User Privilege Table

By default, user information is returned as follows for users authenticated
through RADIUS.

| MPL (privilege)| user info      | uid  | gid  | secondary grps | shell     |
| -------------- | -------------- | ---- | ---- | -------------- | --------- |
| 15             | remote_user_su | 1000 | 1000 | sudo,docker    | /bin/bash |
| 1-14           | remote_user    |65534 |65534 | users          | /bin/rbash|


A different mapping of MPL can be configured in the /etc/radius_nss.conf,
on the switch. For example, if the following lines were added to the
configuration.

```
user_priv=15;pw_info=remote_user_su;uid=1000;gid=1000;group=sudo,docker;dir=/home/admin;shell=/bin/bash
user_priv=7;pw_info=netops;uid=2007;gid=100;group=users;dir=/home/netops;shell=/bin/rbash
user_priv=1;pw_info=operator;uid=2001;gid=100;group=users;dir=/home/operator;shell=/bin/rbash
```

the mapping of MPL would be as follows.

| MPL (privilege)| user info      | uid  | gid  | secondary grps | shell     |
| -------------- | -------------- | ---- | ---- | -------------- | --------- |
| 15             | remote_user_su | 1000 | 1000 | sudo,docker    | /bin/bash |
| 14-7           | netops         | 2007 |  100 | users          | /bin/rbash|
| 1-6            | operator       | 2001 |  100 | users          | /bin/rbash|



## ConfigDB Schema

### AAA Table Schema

```
; Key
aaa_key              = "authentication"   ; AAA type
; Attributes
login                = LIST(1*32VCHAR)   ; pam modules for particular protocol, now only support login for (local, tacacs+, radius). Legal combinations are [ [local], [local, tacacs+ ], [local, radius], [tacacs+, local], [radius, local] ]
failthrough          = "True" / "False"  ; failthrough mechanism for pam modules
```

Note(s):
- protocol = [[tacacs+, local], [radius, local]] are the options
                                                 implementing fallback to local.
- This is an existing table specification, which has been updated for RADIUS

### RADIUS Table Schema

```
; RADIUS configuration attributes global to the system. Only one instance of the table exists in the system. Any of the global RADIUS attributes can be overwritten by the per server settings.
; Key
global_key           = "global"  ;  RADIUS global configuration
; Attributes
passkey              = 1*32VCHAR  ; shared secret (Valid chars: [0-9A-Za-z])
auth_type            = "pap" / "chap" / "mschapv2"  ; method used for authenticating the communication message
src_ip               = IPAddress  ;  source IP address (IPv4 or IPv6) for the outgoing RADIUS packets
timeout              = 1*2DIGIT
retransmit           = 1*2DIGIT
```


### RADIUS_SERVER Table Schema

```
; RADIUS per server configuration in the system.
; Key
server_key           = IPAddress;  RADIUS server's IP address (IPv4 or IPv6)
; Attributes
auth_port            = 1*5DIGIT
passkey              = 1*32VCHAR  ; per server shared secret (Valid chars: [0-9A-Za-z])
auth_type            = "pap" / "chap" / "mschapv2"  ; method used for authenticating the communication message
priority             = 1*2DIGIT  ; specify RADIUS server's priority
timeout              = 1*2DIGIT
retransmit           = 1*2DIGIT
vrf                  = vrf_name  ; If specified, should be VrfMgmt
```

## Manageability

### Data Models

For configuring RADIUS, we will use [Openconfig AAA RADIUS](https://github.com/openconfig/public/blob/master/release/models/system/openconfig-aaa-radius.yang)
Only certain config related parts will be implemented. The supported config
paths are:

- /oc-sys:system/oc-aaa:aaa/oc-aaa:server-groups/oc-aaa:server-group/oc-aaa:server-group=RADIUS_ALL/oc-aaa:servers/oc-aaa:server[address=IPAddress]/config

  The container's oc-aaa:acct-port leaf will not be  supported.

  The container will be augmented to support the following additional leaves:

  - oc-aaa:auth-type
  - oc-aaa:priority
  - oc-aaa:vrf  (If specified, this can only take on the VrfMgmt value.)

  The oc-aaa:server[address=0.0.0.0]/config container will contain the RADIUS
  global configuration attributes.  (i.e. values from the RADIUS table)

  The oc-aaa:source-address leaf will be valid only for the RADIUS global
  configuration (oc-aaa:server[address=0.0.0.0]).

  The oc-aaa:auth-port leaf will be supported only for per server
  (oc-aaa:server[address!=0.0.0.0]) configuration.

### CLI

The RADIUS commands will be implemented in KLISH using the available
CLI framework.

For TACACS+, the existing module click comands will continue to be available.
The AAA commands are an existing click module command which will be extended
for the RADIUS Management User Authentication feature.


```
sonic# show aaa
sonic# show radius

sonic(config)# [no] radius-server source-ip <IPAddress(IPv4 or IPv6)>
sonic(config)# [no] radius-server timeout <0 - 60>
sonic(config)# [no] radius-server retransmit <0 - 10>
sonic(config)# [no] radius-server auth-type [pap | chap | mschapv2]
sonic(config)# [no] radius-server key <TEXT>
sonic(config)# [no] radius-server host <IPAddress(IPv4 or IPv6)>        \
                                     auth-port <1 - 65535>              \
                                     timeout <0 - 60>                   \
                                     retransmit <0 - 10>                \
                                     key <TEXT>                         \
                                     auth-type [pap | chap | mschapv2]  \
                                     priority <1 - 64>                  \
                                     use-mgmt-vrf

$ config aaa authentication login {local | tacacs+ | radius }
$ config aaa authentication failthrough enable/disable

```

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
|         ----                     | --- | config aaa authentication login \  |
|                                  |     |  {local or tacacs+ or radius or...}|
|                                  |     |                                    |
|         ----                     |sonic| config aaa authentication \        |
|                                  |     |  failthrough {enable or disable}   |
|                                  |     |                                    |

Note:
1. For "radius-server source-ip", generally, in the industry we see "ip radius
   source-interface" CLI.


# Flow Diagrams

Please see the sequence diagrams in section [Design](#design)

# Error Handling

PAM and NSS modules return errors as per [Linux-PAM](#Linux-PAM), and
[NSS](#NSS-Reference) respectively.

# Serviceability and Debug

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


