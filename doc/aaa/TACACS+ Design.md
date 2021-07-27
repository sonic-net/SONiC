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
  * [2.4 System log](#24-system-log)
- [3 Limitation](#limitation)
  * [3.1 Command size](#31-command-size)
  * [3.2 Server count](#32-server-count)
- [4 Design](#design)
  * [4.1 Authentication](#41-authentication)
  * [4.2 Authorization](#42-authorization)
    * [4.2.1 Implementation](#421-implementation)
    * [4.2.2 ConfigDB Schema](#422-configdb-schema)
    * [4.2.3 CLI](#423-cli)
  * [4.3 Accounting](#43-accounting)
    * [4.3.1 Implementation](#431-implementation)
    * [4.3.2 ConfigDB Schema](#432-configdb-schema)
    * [4.3.3 CLI](#433-cli)
- [5 Error handling](#error-handling)
- [6 Serviceability and Debug](#serviceability-and-debug)
- [7 Unit Test](#unit-test)
  * [7.1 Unit test for source code](#41-unit-test-for-source-code)
  * [7.2 End to end test with testbed](#41-end-to-end-test-with-testbed)
  * [7.3 Backward compatibility test](#41-backward compatibility test)
- [8 References](#references)
  * [ RFC8907](#rfc8907)
  * [ TACACS+ Authentication](#tacacs+-Authentication)
  * [ Bash](#bash)
  * [pam_tacplus](#pam_tacplus)
  * [ Auditd](#auditd)
  * [ audisp-tacplus](#audisp-tacplus)

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

- Supported Authorization types:
	- EXEC: user session authorization support. this happen when user login.
	- Command: user run command in shell.

- Failover:
	- Authorization will happen before execute, if remote TACACS server not available, use local group based authorization as failover.

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
    config aaa authorization tacacs local
    config aaa authorization local
    config aaa accounting tacacs local
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
 - TACACS protocol limittation: command + parameter size should smaller than 240 byte. The longer than 240 bytes parts will be drop.
 	- This limitation is a protocol level, all TACACS implementation have this limittation, include CISCO, ARISTA and Cumulus.
 	- Both Authorization and Accounting have this limitation.
 	- When user user a command longer than 240 bytes, only commands within 240 bytes will send to TACACS server. which means Accounting may lost some user input. and Authorization check can only partly check user input.


## 3.2 Server count
 - Max TACACS server  count was hardcoded, default count is 8.

# 4 Design
## 4.1 Authentication
 - For Authentication design detail please check [TACACS+ Authentication](#TACPLUS-Authentication)
## 4.2 Authorization
### 4.2.1 Implementation
 - [ Bash](#bash) will be patched to support plugin when user execute disk command.
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

### 4.2.2 ConfigDB Schema
 - The hostcfg enforcer reads data from configDB to configure host environment.
   - The AAA config module in hostcfg enforcer is responsible for modifying Bash configuration files in host.
   - For how TACACS+ config file update please check [TACACS+ Authentication](#TACPLUS-Authentication)

The following figure show how Bash config an TACACS+ config update by ConfigDB.
```
       +-------+  +---------+
       |  SSH  |  | Console |
       +---+---+  +----+----+
           |           |
+----------v-----------v---------+       +---------------------+
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
+---------------+----------------+       +----------^----------+
                                                 |
           +---------+                      +-------+--------+
           |         |                      |                |
           |   CLI   +---------------------->    ConifgDB    |
           |         |                      |                |
           +---------+                      +----------------+
```

### 4.2.3 CLI
 - The existing TACACS+ server config command will not change.
 - Add following command to enable/disable TACACS+ authorizarion.
```
    config aaa authorization tacacs local
    config aaa authorization local
```

 - When config AAA authorization with "no" prefix, SONiC will use local authorization, so following commands have same effect
```
    no config aaa authorization tacacs local
    no config aaa authorization local
    config aaa authorization local
```

## 4.3 Accounting
### 4.3.1 Implementation
### 4.3.2 ConfigDB Schema
### 4.3.3 CLI

# 5 Error handling
[TODO]: add more detail.

# 6 Serviceability and Debug
[TODO]: add more detail.

# 7 Unit Test
## 7.1 Unit test for source code
[TODO]: add more detail.
## 7.2 End to end test
[TODO]: add more detail.
## 7.3 Backward compatibility test
[TODO]: add more detail.

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
