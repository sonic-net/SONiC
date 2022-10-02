# SONiC TACACS+ improvement

# Table of Contents
- [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
- [1 Functional Requirements](#1-functional-requirement)
  * [1.1 User command authorization](#11-user-command-authorization)
  * [1.2 User command accounting](#12-user-command-accounting)
  * [1.3 User script](#13-user-script)
  * [1.4 Multiple TACACS server](#14-multiple-tacas-server)
- [2 Configuration and Management Requirements](#2-configuration-and-management-requirements)
  * [2.1 SONiC CLI](#21-sonic-cli)
  * [2.2 Config DB](#22-config-db)
  * [2.3 Counter](#23-counter)
  * [2.4 Syslog](#24-syslog)
- [3 Limitation](#limitation)
  * [3.1 Command size](#31-command-size)
  * [3.2 Server count](#32-server-count)
  * [3.3 Local authorization](#32-local-authorization)
  * [3.4 Docker support](#34-docker-support)
  * [3.5 Recursive commands](#35-recursive-commands)
- [4 Design](#design)
  * [4.1 Authentication](#41-authentication)
  * [4.2 Authorization Implementation](#42-authorization-implementation)
  * [4.3 Accounting Implementation](#43-accountin-implementationg)
  * [4.4 ConfigDB Schema](#44-configdb-schema)
  * [4.5 CLI](#45-cli)
- [5 Error handling](#error-handling)
- [6 Serviceability and Debug](#serviceability-and-debug)
- [7 Unit Test](#unit-test)
  * [7.1 Unit test for source code](#71-unit-test-for-source-code)
  * [7.2 End to end test with testbed](#72-end-to-end-test-with-testbed)
  * [7.3 Backward compatibility test](#73-backward compatibility test)
- [8 References](#references)
  * [RFC8907](#rfc8907)
  * [TACACS+ Authentication](#tacacs+-Authentication)
  * [Bash](#bash)
  * [pam_tacplus](#pam_tacplus)
  * [Auditd](#auditd)
  * [audisp-tacplus](#audisp-tacplus)
  * [tacplus-auth](#tacplus-auth)

# About this Manual
This document is based on [TACACS+ Authentication](#TACPLUS-Authentication), and provides a detailed description on the new features for improve TACACS+ support.

 - SONiC currently supported TACACS+ features:
   - Authentication.
   - User session authorization.
   - User session accounting.
   - User command authorization with local permission.

 - New features:
   - User command authorization with TACACS+ server.
   - User command accounting with TACACS+ server.

# 1 Functional Requirement
## 1.1 User command authorization
 - Authorization when user run any executable file or script on SONiC host.
   - The full path and parameters will be sent to TACACS+ server side for authorization.
   - For recursive command/script, only the top level command have authorization.
   - No authorization for bash built-in command and bash function, but if a bash function call any executable file or script, those executable file or script will have authorization.

 - TACACS+ authorization is configurable:
   - TACACS+ authorization can be enable/disable.
   - TACACS+ authorization method will communicate with TACACS+ server for authorization, TACACS+ server should setup permit/deny rules.

 - Failover:
   - If a TACACS+ server not accessible, the next TACACS+ server authorization will be performed.
   - When all remote TACACS+ server not accessible, TACACS+ authorization will failed.
   - When TACACS+ authorization failed, fallover is configurable:
     - Disable local authorization as failover, then user can't run any command.
     - Enable local authorization as failover, then user can run command with local authorization.
     - For local authorization, please check [TACACS+ Authentication](#TACPLUS-Authentication).
   - When user login with local account, TACACS+ authentication and authorization will disabled for current user.
     - After login, user can run command with local authorization.
     - When all TACACS+ server not accessible, user can login with this method.
## 1.2 User command accounting
 - Accounting is the action of recording what a user is doing, and/or has done.

 - Following event will be accounted:
   - Command start event.
   - Command finish event.

 - User command inside docker container will not be accounted.
   - User command inside docker container actually run by docker service, so we can't identify if command are run by user or system service.
   - The 'docker exec <container> <process>' command will be accounted because it's not run inside docker container.

 - Support TACACS+ accounting and local accounting:
   - TACACS+ will send event to TACACS+ server, and communication will be encrypted, for more detail please check [RFC8907](#rfc8907).
   - Local accounting will save event to syslog.
   - Both TACACS+ accounting and local accounting are configurable.

 - User secrets not exist in accounting event:
   - Use regex in /etc/sudoers PASSWD_CMDS to identify user secrets.
   - User secret will be replaced with ***.

## 1.3 User script
 - User can create and run their own script. 
 - User may run script with interpreter commands:
   - python ./userscript.txt
   - sh ./usershellscript.txt
 - Allow user create and run script may cause potensial security issue, so suggest administrator setup rules from TACACS+ server side to block RO user create and run script.

## 1.4 Multiple TACACS server
 - Support config multiple TACACS server.
 - First server in the list will be primary server.
 - When a server not accessible, will try next server as backup.
 - When all server not accessible from SONiC, use native failover solution.

# 2 Configuration and Management Requirements
## 2.1 SONiC CLI
 - Enable/Disable TACACS Authorization/Accounting command
```
    config aaa authorization {local | tacacs+ | local tacacs+}
    config aaa accounting {local | tacacs+ | disable}
```

 - Counter command
```
    show tacacs+ counter
    sonic-clear tacacscounters
```

## 2.2 Config DB
 - TACACS AAA are fully configurable by config DB.

## 2.3 Counter
 - Support AAA counter, this will be low priority:
```
    show tacacs+ counter
    
        server1: 10.1.1.45
        Messages sent: 24
        Messages received: 20
        Requests accepted: 14
        Requests rejected: 8
        Requests timeout: 2
        Requests retransmitted: 1
        Bad responses: 1
```

## 2.4 Syslog
 - Generate syslog when Authentication/Authorization/Accounting.
 - When remote TACACS server not accessible from SONiC, use syslog for accounting.


# 3 Limitation
## 3.1 Command size
 - TACACS protocol limitation: command + parameter size should smaller than 240 byte. The longer than 240 bytes parts will be drop.
 	- This limitation is a protocol level, all TACACS implementation have this limitation, include CISCO, ARISTA and Cumulus.
 	- Both Authorization and Accounting have this limitation.
 	- When user user a command longer than 240 bytes, only commands within 240 bytes will send to TACACS server. which means Accounting may lost some user input. and Authorization check can only partly check user input.

## 3.2 Server count
 - Max TACACS server count was hardcoded, default count is 8.

## 3.3 Local authorization
 - Operation system limitation: SONiC based on Linux system, so permission to execute local command are managed by Linux file permission control. This means when enable both TACACS+ authorization and local authorization, local authorization will always happen after TACACS+ authorization.

## 3.4 Docker support
 - Any command run inside a shell in a docker container will not covered by Authorization and Accounting.
 - Docker exec command will be covered by Authorization and Accounting. 
 - Administrator may setup TACACS+ rules to block docker exec command for RO user:
   - user can start an interactive shell on the docker container, then run command inside container to evade TACACS+ authorization and accounting.

## 3.5 Recursive commands
  - Many linux command allow user start a harmless process and run another command from it, administrator may setup TACACS+ rules from server side to block user from:
    - Run another shell.
    - Run interpreter, for example python.
    - Run loader, for example /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
    - Run find/VI command which can run other commands inside it.

# 4 Design
## 4.1 Authorization Implementation
 - [Bash](#bash) will be patched to support plugin when user execute disk command.
 - A bash plugin to support TACACS+ authorization.
   - Use TACACS+ setting from TACACS+ authentication.
   - Use libtac library from [pam_tacplus](#pam_tacplus) for TACACS+ protocol.

The following figure show how Bash plugin work with TACACS+ server.
```
       +-------+  +---------+
       |  SSH  |  | Console |
       +---+---+  +----+----+
           |           |
+----------v-----------v---------+       +---------------------+
| Bash                           |       |                     |
|                                |       |                     |
|   +-------------------------+  |       |                     |
|   |     TACACS+ plugin      +---------->    TACACS+ server   |
|   +-------------------------+  |       |                     |
|                                |       |                     |
|                                |       |                     |
+---------------+----------------+       +---------------------+
```

Following is the sequence of events during TACACS+ authorization user command:

```
SSH/Console           SONiC Device                     TACACS+ Server
                  /bin/Bash     Bash Plugin
----------------------------------------------------------------------

    |                 |                 |                    |
    |                 |                 |                    |
    | User Command(1) |                 |                    |
    +---------------->|                 |                    |
    |                 |                 |                    |
    |                 +---------------->|                    |
    |                 |                 |   Authorization    |
    |                 |                 |     Request(2)     |
    |                 |                 +------------------->|
    |                 |                 |                    |
    |                 |                 |   Authorization    |
    |                 |                 |     Result(3)      |
    |                 |                 |--------------------+
    |                 |                 |                    |
    |                 |<----------------+                    |
    |                 |                 |                    |
    |                 |                 |                    |
    |  Success(4)     |                 |                    |
    |<----------------|                 |                    |
    |                 |                 |                    |

```

 - The hostcfg enforcer reads data from configDB to configure host environment.
   - The AAA config module in hostcfg enforcer is responsible for modifying Bash configuration files in host. this will be low priority.
   - For how TACACS+ config file update, please check [TACACS+ Authentication](#TACPLUS-Authentication)

The following figure show how Bash config and TACACS+ config update by ConfigDB.
```
+--------------------------------+       +---------------------+
| Bash                           |       |                     |
|   +-------------------------+  |       |  +--------------+   |
|   | Bash config file        <-------------+ Authorization|   |
|   |                         |  |       |  |    Config    |   |
|   +-------------------------+  |       |  +--------------+   |
|                                |       |                     |
|   +-------------------------+  |       |  +--------------+   |
|   | TACACS+ config file     <-------------+  AAA Config  |   |
|   +-------------------------+  |       |  +--------------+   |
|                                |       |                     |
|                                |       |  HostCfg Enforcer   |
+--------------------------------+       +----------^----------+
                                                    |
           +---------+                      +-------+--------+
           |         |                      |                |
           |   CLI   +---------------------->    ConifgDB    |
           |         |                      |                |
           +---------+                      +----------------+
```

 - [tacplus-auth](#tacplus-auth) is another open source project for TACACS+ authorization, not use this solution because following limitation:
   - Using symbol link for command authorization, need create new symbol link in local and update remote server to support new command.
   - Using rbash to restrict user can only access symbol linked commands, which also disable some useful bash feature.

## 4.2 Accounting Implementation
 - [Auditd](#auditd) will enable on SONiC to provide syscall event for accounting.
 - [audisp-tacplus](#audisp-tacplus) is a Auditd plugin that support TACACS+ Accounting (user command).
 - Pam_tacplus will provide session accounting, please check [TACACS+ Authentication](#TACPLUS-Authentication)

The following figure show how audisp-tacplus work with TACACS+ server.
```
         +-----------------+
         |  Syscall Event  |
         +-------+---------+
                 |
+----------------v---------------+       +---------------------+
| Auditd                         |       |                     |
|                                |       |                     |
|   +-------------------------+  |       |                     |
|   |     audisp-tacplus      +---------->    TACACS+ server   |
|   +-------------------------+  |       |                     |
|                                |       |                     |
|                                |       |                     |
+---------------+----------------+       +---------------------+
```


 - The hostcfg enforcer reads data from configDB to configure host environment.
   - The AAA config module in hostcfg enforcer is responsible for modifying Auditd configuration files in host. this will be low priority.
   - For how TACACS+ config file update, please check [TACACS+ Authentication](#TACPLUS-Authentication)

The following figure show how Auditd config an TACACS+ config update by ConfigDB.
```
+--------------------------------+       +---------------------+
| Auditd                         |       |                     |
|   +-------------------------+  |       |  +--------------+   |
|   | Auditd config file      <-------------+ Accounting   |   |
|   |                         |  |       |  |    Config    |   |
|   +-------------------------+  |       |  +--------------+   |
|                                |       |                     |
|   +-------------------------+  |       |  +--------------+   |
|   | TACACS+ config file     <-------------+  AAA Config  |   |
|   +-------------------------+  |       |  +--------------+   |
|                                |       |                     |
|                                |       |  HostCfg Enforcer   |
+--------------------------------+       +----------^----------+
                                                    |
           +---------+                      +-------+--------+
           |         |                      |                |
           |   CLI   +---------------------->    ConifgDB    |
           |         |                      |                |
           +---------+                      +----------------+
```


## 4.3 ConfigDB Schema
 - Existing tables, for more detail please check [TACACS+ Authentication](https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md#aaa-table-schema)
   - TACPLUS Table
   - TACPLUS_SERVER Table.
   - AAA Table (updated).
```
; Key
aaa_key              = 1*32VCHAR          ; AAA type "authentication"/"authorization"/"accounting"
; Attributes
login                = LIST(1*32VCHAR)   ; AAA protocol, now only support (local, tacacs+)
fallback             = "True" / "False"  ; fallback mechanism for pam modules
failthrough          = "True" / "False"  ; failthrough mechanism for pam modules
```
* According to [TACACS+ Authentication](https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md#aaa-table-schema), the 'login' attribute should be 'protocol' attribute , But in current SONiC [yang model](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-system-aaa.yang), this attribute name is 'login'. Because change the attribute name may break backward compatibility, so keep will use 'login' as attribute name.

## 4.4 CLI
 - The existing TACACS+ server config command will not change.
 - Add following command to enable/disable authorization.
```
    // authorization with TACACS+ server and local
    config aaa authorization tacacs+ local
    
    // authorization with TACACS+ server
    config aaa authorization tacacs+
    
    // authorization with local, disable tacacs authorization
    config aaa authorization local
```

 - Add following command to enable/disable accounting.
```
    // accounting with TACACS+ server and local syslog
    config aaa accounting tacacs+ local

    // accounting with TACACS+ server
    config aaa accounting tacacs+

    // accounting with local syslog
    config aaa accounting local
```

 - Following command will disable accounting
```
    config aaa accounting disable
```
# 5 Error handling
 - Bash plugin for authorization will return error code [Bash](#bash). and patched Bash will:
   - Output error log to syslog.
   - Output error message to stderr.
 - [audisp-tacplus](#audisp-tacplus) will return errors as per [Auditd](#auditd)  respectively.

# 6 Serviceability and Debug
 - The Bash plugin and [audisp-tacplus](#audisp-tacplus) can be debugged by enabling the debug
field of the AAA|authentication key. (Please see ConfigDB AAA Table
Schema in [TACACS+ Authentication](#TACPLUS-Authentication)). 

# 7 Unit Test
## 7.1 Unit test for source code
 - All patch code in Bash and Bash plugin should have 100% code coverage.
 - Bash plugin test, all TACACS+ server not reachable test:
```
    Verify TACACS+ authorization failed.
```

 - Bash plugin test, partial TACACS+ server accessible, and user command config as allowed on all server.
```
    Verify TACACS+ authorization passed.
```

 - Bash plugin test, partial TACACS+ server accessible, and user command config as reject on all server.
```
    Verify TACACS+ authorization rejected.
```

 - Bash plugin test, partial TACACS+ server accessible, and user command config as reject on accessible server, and allow on not accessible server.
```
    Verify TACACS+ authorization rejected.
```

 - Bash plugin test, partial TACACS+ server accessible, and user command config as allow on accessible server, and reject on not accessible server.
```
    Verify TACACS+ authorization passed.
```

 - [audisp-tacplus](#audisp-tacplus) test, all TACACS+ server accessible.
```
    Verify TACACS+ accounting succeeded.
```

 - [audisp-tacplus](#audisp-tacplus) test, all TACACS+ server not accessible.
```
    Verify plugin return correct error code.
```

 - [audisp-tacplus](#audisp-tacplus) test, partial TACACS+ server accessible.
```
    Verify TACACS+ accounting succeeded.
```

 - [audisp-tacplus](#audisp-tacplus) test, user command longer than 240 bytes.
```
    Verify TACACS+ accounting succeeded.
    Verify only 240 bytes of user command send to TACACS+ server side.
```

 - [audisp-tacplus](#audisp-tacplus) test, user command+parameter longer than 240 bytes.
```
    Verify TACACS+ accounting succeeded.
    Verify only 240 bytes of user command+parameter send to TACACS+ server side.
```

## 7.2 End to end test

- config AAA authorization with TACACS+ only:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
    Verify Local user can't login.
```

- config AAA authorization with TACACS+ only:
    - when user login server are accessible.
    - user run some command in whitelist and server are accessible.
    - then all server not accessible, and run some command
```
    Verify when server are accessible, TACACS+ user can run command in server side whitelist.
    Verify when server are not accessible, TACACS+ user can't run any command.
```

- config AAA authorization with TACACS+ only and some server not accessible:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
    Verify Local user can't login.
```

- config AAA authorization with TACACS+ and local:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
    Verify Local user can't login.
```

- config AAA authorization with TACACS+ and local, but server not accessible:
```
    Verify TACACS+ user can run command not in server side whitelist but have permission in local.
    Verify TACACS+ user can't run command in server side whitelist but not have permission in local.
    Verify Local user can login, and run command with local permission.
    Verify after Local user login, then server becomes accessible, Local user still can run command with local permission.
```

- config AAA authorization with local:
```
    Verify TACACS+ user can run command if have permission in local.
    Verify TACACS+ user can't run command if not have permission in local.
    Verify Local user can login, and run command with local permission.
```

- config AAA accounting with TACACS+ only:
```
    Verify TACACS+ server have user command record.
    Verify TACACS+ server not have any command record which not run by user.
```

- config AAA accounting with TACACS+ only:
    - when user login server are accessible.
    - user run some command in whitelist and server are accessible.
    - then all  server not accessible, and run some command
```
    Verify local user still can run command without any issue.
```

- config AAA accounting with TACACS+ only and some server not accessible:
```
    Verify syslog have user command record.
    Verify syslog not have any command record which not run by user.
```

- config AAA accounting with TACACS+ and local:
```
    Verify TACACS+ server and syslog have user command record.
    Verify TACACS+ server and syslog not have any command record which not run by user.
```

- config AAA accounting with TACACS+ and local, but all server not accessible:
```
    Verify TACACS+ user can run command not in server side whitelist but have permission in local.
    Verify TACACS+ user can't run command in server side whitelist but not have permission in local.
```

- config AAA accounting with local:
```
    Verify syslog have user command record.
    Verify syslog not have any command record which not run by user.
```

- prevent user bypass TACACS+ authorization test:
    - Setup TACACS+ server side rules:
      - Disable user run python, sh command.
      - Disable user run find with '-exec'
      - Disable user run /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
```
    Verify user can't run script with sh/python with following command.
        python ./testscript.py
    Verify user can't run 'find' command with '-exec' parameter.
    Verify user can run 'find' command without '-exec' parameter.
    Verify user can't run command with loader:
        /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 sh
    Verify user can't run command with prefix/quoting:
        \sh
        "sh"
        echo $(sh -c ls)
```

## 7.3 Backward compatibility test

- config disable AAA authorization and accounting:
```
    Verify domain account can login to device successfully.
    Verify domain account can run command if have permission in local.
    Verify domain account can login to device successfully.
    Verify local admin account can login to device successfully.
    Verify local admin account can run command if have permission in local.
    Verify local admin account can't run command if not have permission in local.
```

- config enable AAA authorization and accounting, and run all existing AAA authentication test case:
```
    Verify all test case not break.
```

# 8 References
## RFC8907
https://datatracker.ietf.org/doc/html/rfc8907
## TACACS+ Authentication
https://github.com/sonic-net/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md
## Bash
https://www.gnu.org/software/bash/html
## pam_tacplus
https://github.com/kravietz/pam_tacplus
## auditd
http://man7.org/linux/man-pages/man8/auditd.8.html
## audisp-tacplus
https://github.com/daveolson53/audisp-tacplus
## tacplus-auth
https://github.com/daveolson53/tacplus-auth
