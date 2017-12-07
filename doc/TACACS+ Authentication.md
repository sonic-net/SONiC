# TACACS+ Authentication

## Overview

TACACS+ (Terminal Access Controller Access-Control System Plus) is an authentication protocol that allows a remote access server to forward a login password for a user to an authentication server to determine whether access is allowed to a given system. In addition to the authentication service, TACACS+ can also provide authorization and accounting services.

Pluggable authentication modules (PAM) are at the core of user authentication in any modern linux distribution. PAM uses a pluggable, modular architecture, which affords the system administrator a great deal of flexibility in setting authentication policies for the system.

## Requirements

- Support TACACS+ login authentication for SSH and console.
- Source IP address for TACACS+ packets can be specified.
- Support multiple TACACS+ server, and the priority of the server can be configured.
- Support to set the order of local authentication and TACACS+ authentication.
- Support fail_through mechanism for authentication. If a TACACS+ server authentication fails, the next TACACS+ server authentication will be performed.
- Authentication for root is only specified in local.

## Assumptions

- When user login to the box, user will land at Linux shell.
- TACACS+ Authenticated users are remote users need not be configured with the switch. So these TACACS+ Authenticated users will map to a remote user profile after TACACS+ Authentication.

## Implementation

The hostcfg enforcer reads data from configDB to configure host environment. The AAA config module in hostcfg enforcer is responsible for modifying PAM configuration files in host.

```
       +-------+  +---------+
       |  SSH  |  | Console |
       +---+---+  +----+----+
           |           |
+----------v-----------v---------+       +---------------------+
| AUTHENTICATION                 |       |                     |
|   +-------------------------+  |       |  +------------+     |
|   | PAM Configuration Files <-------------+ AAA Config |     |
|   +-------------------------+  |       |  +------------+     |
|                                |       |                     |
|         +-------------+        |       |  HostCfg Enforcer   |
|         |     PAM     |        |       +----------^----------+
|         |  Libraries  |        |                  |
|         +-------------+        |                  |
+---------------+----------------+                  |
                |                                   |
           +----v----+                      +-------+--------+
           |         |                      |                |
           |   CLI   +---------------------->    ConifgDB    |
           |         |                      |                |
           +---------+                      +----------------+

```

### pam_tacplus

Pam_tacplus is a TACACS+ client toolkit that supports core TACACS+ functions: Authentication, Authorization (account management) and Accounting (session management). It supports many options for authentication, such as server, secret, timeout, but no source IP address. So a patch for source IP address is added in pam_tacplus.

### nss_tacplus

Normally, TACACS+ is only used for AAA, but not for nameservice. Without a plugin like nss_ldap to extend NSS (Name Service Switch), the TACACS+ authenticated user which is not found in local password file will login fails.

Nss_tacplus is a NSS plugin which provides the getpwnam_r() entry point. It makes a connection to TACACS+ server to retrieve user privilege and validate user. If username is found in /etc/passwd, it will fill buffer with password info and return found. If not found, a local user is created with the same as the authenticated user.

To make connection to TACACS+ server, nss_tacplus need to load configuration file /etc/tacplus_nss.conf to get configurations for TACACS+ server. AAA config module in HostCfg Enforcer is responsible for modifying TACACS+ server configuration in tacplus_nss.conf.

#### User Privilege Table

To create a local user with necessary password info (gid, secondary groups, shell, home directory) which can distinguish the user role, user privilege table in nss_tacplus should be created. The table is defined with two user role by default, and it also can be configured by the configuration file /etc/tacplus_nss.conf.

| user privilege | user info | gid | secondary groups | shell |
| -------------- | --------- | --- | ---------------- | ----- |
| 15 | remote_user_su | 1000 | sudo,docker | /bin/bash |
| 1 ~ 14 | remote_user | 999 | docker | /bin/bash |

If configurations with two user privilege are inserted in /etc/tacplus_nss.conf, the privilege table will be changed as follows.

```
user_priv=7;pw_info=netops;gid=999;group=docker;shell=/bin/bash
user_priv=1;pw_info=operator;gid=999;group=docker;shell=/bin/rbash
```

| user privilege | user info | gid | secondary groups | shell |
| -------------- | --------- | --- | ---------------- | ----- |
| 15 | remote_user_su | 1000 | sudo,docker | /bin/bash |
| 14 ~ 7 | netops | 999 | docker | /bin/bash |
| 1 ~ 6 | operator | 999 | docker | /bin/rbash |

Note: The user's home directory is created as the username in /home.

#### Enable nss_tacplus

The plugin nss_tacplus is disabled by default. Only if TACACS+ Authentication is enabled, 'tacplus' is added in /etc/nsswitch.conf and nss_tacplus can be called.

```
# /etc/nsswitch.conf
#
# Example configuration of GNU Name Service Switch functionality.
# If you have the `glibc-doc-reference' and `info' packages installed, try:
# `info libc "Name Service Switch"' for information about this file.

passwd:         compat tacplus
group:          compat
...
```

### PAM configuration

The PAM configuration in /etc/pam.d/common-auth is included in login or ssh authentication by default in Linux. If TACACS+ Authentication is enabled, a new PAM configuration file “common-auth-sonic” is created and replaced in login and ssh, and the other application which authentication include “common-auth” will not be affected.

- PAM configuration with two TACACS+ server and 'source address' configuration, 'fail_through' mechanism is disabled

```
auth	[success=done new_authtok_reqd=done default=ignore auth_err=die]	pam_unix.so nullok try_first_pass

auth	[success=done new_authtok_reqd=done default=ignore auth_err=die]	pam_tacplus.so server=10.65.254.222:49 secret=test123 login=pap timeout=3 source_ip=100.0.0.9 try_first_pass

auth	[success=1 default=ignore]	pam_tacplus.so server=10.65.254.248:49 secret=test123 login=pap timeout=3 source_ip=100.0.0.9 try_first_pass

# here's the fallback if no module succeeds
auth    requisite                       pam_deny.so
auth    required                        pam_permit.so
```

- PAM configuration with 'fail_through' mechanism

```
auth	[success=done new_authtok_reqd=done default=ignore]	pam_unix.so nullok try_first_pass

auth	[success=1 new_authtok_reqd=done default=ignore]	pam_tacplus.so server=10.65.254.223:49 secret=test123 login=pap timeout=5  try_first_pass

# here's the fallback if no module succeeds
auth    requisite                       pam_deny.so
auth    required                        pam_permit.so
```

- PAM configuration which TACACS+ authentication is prior to local authentication

```
auth	[success=1 new_authtok_reqd=done default=ignore]	pam_succeed_if.so user = root debug

auth	[success=done new_authtok_reqd=done default=ignore]	pam_tacplus.so server=10.65.254.222:49 secret=test123 login=pap timeout=3 try_first_pass

auth	[success=1 default=ignore]	pam_unix.so nullok try_first_pass

# here's the fallback if no module succeeds
auth    requisite                       pam_deny.so
auth    required                        pam_permit.so
```

### ConfigDB schema

#### AAA Table schema

```
; Key
aaa_key              = "authentication"   ; AAA type
; Attributes
protocol             = LIST(1*32VCHAR)   ; pam modules for particular protocol, now only support login for (local, tacacs+)
fallback             = "True" / "False"  ; fallback mechanism for pam modules
failthrough          = "True" / "False"  ; failthrough mechanism for pam modules
```

#### TACPLUS Table schema

```
; TACACS+ configuration attributes global to the system. Only one instance of the table exists in the system. Any of the global TACACS+ attribute can be overwritten by a fine grained per server setting.
; Key
global_key           = “global”  ;  TACACS+ global configuration
; Attributes
passkey              = 1*32VCHAR  ; shared secret used for encrypting the communication
auth_type            = "pap" / "chap" / "mschap"  ; method used for authenticating the communication message
src_ip               = IPAddress  ;  source ip address for the outgoing TACACS+ packets
timeout              = 1*2DIGIT
```

#### TACPLUS_SERVER Table schema

```
; TACACS+ server configuration in the system.
; Key
server_key           = IPAddress  ;  TACACS+ server’s address
; Attributes
tcp_port             = 1*5DIGIT
passkey              = 1*32VCHAR  ; shared secret used for encrypting the communication
auth_type            = "pap" / "chap" / "mschap"  ; method used for authenticating the communication message
priority             = 1*2DIGIT  ; specify TACACS+ server’s priority
timeout              = 1*2DIGIT
```

### Command

AAA and TACACS+ command is implemented by using click module in sonic-utilities. The current support commands are as defined as follows:

```
config aaa authentication login {local | tacacs+}
config aaa authentication failthrough enable/disable

show aaa

config tacacs src_ip <ADDRESS>
config tacacs timeout <0 – 60>
config tacacs authtype [pap | chap | mschap]
config tacacs passkey <TEXT>
config tacacs add <ADDRESS> --port <1 – 65535>
                            --timeout <0 – 60>
                            --key <TEXT>
                            --type [pap | chap | mschap]
                            --pri <1 - 64>
config tacacs delete <ADDRESS>

show tacacs
```
