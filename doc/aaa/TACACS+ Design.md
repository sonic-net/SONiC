# SONiC TACACS+ protocol Design

# Table of Contents
- [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
- [1 Functional Requirements](#1-functional-requirement)
  * [1.1 Authentication](#11-authentication)
  * [1.2 Authorization](#12-authorization)
  * [1.3 Accounting](#13-accounting)
  * [1.4 User script](#14-user-script)
  * [1.5 Docker support](#15-docker-support)
  * [1.6 Multiple TACACS server](#16-multiple-tacas-server)
- [2 Configuration and Management Requirements](#2-configuration-and-management-requirements)
  * [2.1 SONiC CLI](#21-sonic-cli)
  * [2.2 Config DB](#22-config-db)
  * [2.3 Counter](#23-counter)
  * [2.4 Syslog](#24-syslog)
- [3 Limitation](#limitation)
  * [3.1 Command size](#31-command-size)
  * [3.2 Server count](#32-server-count)
  * [3.3 Local authorization](#32-local-authorization)
- [4 Design](#design)
  * [4.1 Authentication](#41-authentication)
  * [4.2 Authorization Implementation](#42-authorization-implementation)
  * [4.3 Accounting Implementation](#43-accountin-implementationg)
  * [4.4 ConfigDB Schema](#44-configdb-schema)
  * [4.5 CLI](#45-cli)
- [5 Error handling](#error-handling)
- [6 Serviceability and Debug](#serviceability-and-debug)
- [7 Unit Test](#unit-test)
  * [7.1 Unit test for source code](#41-unit-test-for-source-code)
  * [7.2 End to end test with testbed](#41-end-to-end-test-with-testbed)
  * [7.3 Backward compatibility test](#41-backward compatibility test)
- [8 References](#references)
  * [RFC8907](#rfc8907)
  * [TACACS+ Authentication](#tacacs+-Authentication)
  * [Bash](#bash)
  * [pam_tacplus](#pam_tacplus)
  * [Auditd](#auditd)
  * [audisp-tacplus](#audisp-tacplus)
  * [tacplus-auth](#tacplus-auth)

# About this Manual
This document provides a detailed description on the requirement and design of TACACS+ protocol support.

# 1 Functional Requirement
## 1.1 Authentication
- Authentication when user login to SONiC host.
- For more detail please check [TACACS+ Authentication](#TACPLUS-Authentication)


## 1.2 Authorization
- Authorization when:
	- User login to SONiC host.
	- User run any executable file or script on SONiC host.
      - The full path and parameters will be send to TACACS+ server side for authorization.
      - For recursive command/script, only the top level command have authorization.
        - No authorization for  bash builtin command and bash function, but if a bash function call any executable file or script, those executable file or script will have authorization.
      - Commands entered through the console not have authorization by default.

- Supported Authorization types:
    - EXEC: user session authorization support. this happen when user login.
    - Command: user run command in shell.

- Support to set the local authorization and TACACS+ authorization.
    - Local authorization method is based on Linux permission control.
      - Local authorization can't be disabled, and must be the last authorization method, for detail please check [3.3 Local authorization](#32-local-authorization)	
      - Authorization for root and admin can only specified as local.
    - TACACS+ authorization method will send  to TACACS+ server for authorization, TACACS+ server should setup permit/deny rules.

- Failover:
    - If a TACACS+ server not accessable, the next TACACS+ server authorization will be performed.
	- When all remote TACACS+ server not accessible, TACACS+ authorization will failed.
	- When set TACACS+ as the only authorization method, if all TACACS+ server not accessible, user cannot run any command on SONiC device.

## 1.3 Accounting
 - Accounting is the action of recording what a user is doing, and/or has done.

 - Following event will be accounted:
 	- User login to SONiC host.
 	- User logout.
 	- User run command on host: 
		- Command start run.
		- Command finish.

- User command in Docker will not be accounted.
    - User command in docker actually run by docker service, so we can't identify if command are run by user or system service.
	
- Failover:
	- Use syslog as backup when remote TACACS not not accessible from SONiC.


## 1.4 User script
 - User can create and run their own script. 
 - If user create a script but TACACS+ service side not have configuration to allow user run this script, user script will be blocked by authorization.

## 1.5 Docker support
 - Docker exec command will be covered by Authorization and Accounting. 
 - Any command run inside docker container will not covered by Authorization and Accounting.

## 1.6 Multiple TACACS server
 - Support config multiple TACACS server.
 - When a server not accessible, will try next server as backup.
 - When all server not accessible from SONiC, use native failover solution.

# 2 Configuration and Management Requirements
## 2.1 SONiC CLI
 - Enable/Disable TACACS Authorization/Accounting command
```
	config aaa authorization {local | tacacs+}
    config aaa accounting {local | tacacs+}
    config aaa accounting local
```

 - Counter command
```
    show tacacs counter
    sonic-clear tacacscounters
```

## 2.2 Config DB
 - TACACS AAA are fully configable by config DB.

## 2.3 Counter
 - Support  AAA counter:
```
    show tacacs counter
    
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
 	- This limitation is a protocol level, all TACACS implementation have this limittation, include CISCO, ARISTA and Cumulus.
 	- Both Authorization and Accounting have this limitation.
 	- When user user a command longer than 240 bytes, only commands within 240 bytes will send to TACACS server. which means Accounting may lost some user input. and Authorization check can only partly check user input.

## 3.2 Server count
 - Max TACACS server  count was hardcoded, default count is 8.

## 3.3 Local authorization
 - Operation system limitation: SONiC based on linux system, so permission to execute local command are managed by Linux file permission control. This means TACACS+ authorization can't config to disable 'local' authorization, and local authorization must be last authorization in authorization method list.

# 4 Design
## 4.1 Authentication
 - For Authentication design, please check [TACACS+ Authentication](#TACPLUS-Authentication)

## 4.2 Authorization Implementation
 - Pam_tacplus will provide Authorization for login (account management), please check [TACACS+ Authentication](#TACPLUS-Authentication)
 - [Bash](#bash) will be patched to support plugin when user execute disk command.
 - A bash plugin to support TACACS+ authorization.
   - Use TACACS+ setting from TACACS+ authentication.
   - Use libtac library from [pam_tacplus](#pam_tacplus) for TACACS+ protocol.
   - Bash configration file for root user not enable this plugin, root user only use local Authorization. 

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

Following is the sequence of events during TACACS+ authoriztaion user command:

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
   - The AAA config module in hostcfg enforcer is responsible for modifying Bash configuration files in host.
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

## 4.3 Accounting Implementation
 - [Auditd](#auditd) will enable on SONiC to provide syscall event for accounting.
 - [audisp-tacplus](#audisp-tacplus) is a Auditd plugin that support TACACS+ Acounting (user command).
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
   - The AAA config module in hostcfg enforcer is responsible for modifying Auditd configuration files in host.
   - For how TACACS+ config file update, please check [TACACS+ Authentication](#TACPLUS-Authentication)

The following figure show how Auditd config an TACACS+ config update by ConfigDB.
```
+--------------------------------+       +---------------------+
| Auditd                         |       |                     |
|   +-------------------------+  |       |  +--------------+   |
|   | Auditd config file      <-------------+ Accounting   |
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


## 4.4 ConfigDB Schema
 - TACACS+ Authorization and Accounting will use existing tables
   - AAA Table.
   - TACPLUS Table
   - TACPLUS_SERVER Table.

 - For more detail of existing tables, please check [TACACS+ Authentication](#TACPLUS-Authentication)

## 4.5 CLI
 - The existing TACACS+ server config command will not change.
 - Add following command to enable/disable TACACS+ authorizarion.
```
    // authorization with TACACS+ server and local
    config aaa authorization tacacs local
    
    // authorization with TACACS+ server
    config aaa authorization tacacs
    
    // authorization with TACACS+ local
    config aaa authorization local
```

 - Add following command to enable/disable TACACS+ accounting.
```
    // accounting with TACACS+ server and local syslog
    config aaa accounting tacacs local

    // accounting with TACACS+ server
    config aaa accounting tacacs

    // accounting with local syslog
    config aaa accounting local
```

 - When config AAA authorization with "no" prefix, SONiC will use local authorization, so following commands have same effect
```
    no config aaa authorization tacacs local
    no config aaa authorization local
    config aaa authorization local
```

 - When config AAA accounting with "no" prefix, SONiC will use stop accounting, following command have same effect.
```
    no config aaa authorization tacacs local
    no config aaa authorization tacacs
    no config aaa authorization local
```
# 5 Error handling
 - Bash plugin for authorization will return error code [Bash](#bash). and patched Bash will:
   - Output error log to syslog.
   - Output error message to stdout.
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

 - Bash plugin test, partial TACACS+ server accessable, and user command config as allowed on all server.
```
    Verify TACACS+ authorization passed.
```

 - Bash plugin test, partial TACACS+ server accessable, and user command config as reject on all server.
```
    Verify TACACS+ authorization rejected.
```

 - Bash plugin test, partial TACACS+ server accessable, and user command config as reject on accessable server, and allow on not accessable server.
```
    Verify TACACS+ authorization rejected.
```

 - Bash plugin test, partial TACACS+ server accessable, and user command config as allow on accessable server, and reject on not accessable server.
```
    Verify TACACS+ authorization passed.
```

 - [audisp-tacplus](#audisp-tacplus) test, all TACACS+ server accessable.
```
    Verify TACACS+ accounting succeeded.
```

 - [audisp-tacplus](#audisp-tacplus) test, all TACACS+ server not accessable.
```
    Verify plugin return correct error code.
```

 - [audisp-tacplus](#audisp-tacplus) test, partial TACACS+ server accessable.
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

- config aaa authorization with TACACS+ only:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
```

- config aaa authorization with TACACS+ only and all  server not accessable:
```
    Verify TACACS+ user can't run any command.
```

- config aaa authorization with TACACS+ only and some server not accessable:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
```

- config aaa authorization with TACACS+ and local:
```
    Verify TACACS+ user run command in server side whitelist:
        If command have local permission, user can run command.
        If command not have local permission, user can't run command.
    Verify TACACS+ user can't run command not in server side whitelist.
```

- config aaa authorization with TACACS+ and local, but server not accessable:
```
    Verify TACACS+ user can run command not in server side whitelist but have permission in local.
    Verify TACACS+ user can't run command in server side whitelist but not have permission in local.
```

- config aaa authorization with local:
```
    Verify TACACS+ user can run command if have permission in local.
    Verify TACACS+ user can't run command if not have permission in local.
```

- config aaa accounting with TACACS+ only:
```
    Verify TACACS+ server have user command record.
    Verify TACACS+ server not have any command record which not run by user.
```

- config aaa accounting with TACACS+ only and all server not accessable:
```
    Verify local user still can run command without any issue.
```

- config aaa accounting with TACACS+ only and some server not accessable:
```
    Verify syslog have user command record.
    Verify syslog not have any command record which not run by user.
```

- config aaa accounting with TACACS+ and local:
```
    Verify TACACS+ server and syslog have user command record.
    Verify TACACS+ server and syslog not have any command record which not run by user.
```

- config aaa accounting with TACACS+ and local, but all server not accessable:
```
    Verify TACACS+ user can run command not in server side whitelist but have permission in local.
    Verify TACACS+ user can't run command in server side whitelist but not have permission in local.
```

- config aaa accounting with local:
```
    Verify syslog have user command record.
    Verify syslog not have any command record which not run by user.
```


## 7.3 Backward compatibility test

- config disable aaa authorization and accounting:
```
    Verify GME user can login to device successfully.
    Verify GME user can run command if have permission in local.
    Verify GME user can login to device successfully.
    Verify admin user can login to device successfully.
    Verify admin user can run command if have permission in local.
    Verify admin user can't run command if not have permission in local.
```

- config enable aaa authorization and accounting, and run all existing aaa authencation test case:
```
    Verify all test case not break.
```

# 8 References
## RFC8907
https://datatracker.ietf.org/doc/html/rfc8907
## TACACS+ Authentication
https://github.com/Azure/SONiC/blob/master/doc/aaa/TACACS%2B%20Authentication.md
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
