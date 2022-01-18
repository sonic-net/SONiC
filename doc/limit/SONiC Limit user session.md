# SONiC Limit user login session

# Table of Contents
- [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
- [1 Functional Requirements](#1-functional-requirement)
  * [1.1 Limit the login session per user/group/system](#11-limit-the-login-session-per-user/group/system)
  * [1.3 Default limitation](#13-default-limitation)
- [2 Configuration and Management Requirements](#2-configuration-and-management-requirements)
  * [2.1 SONiC CLI](#21-sonic-cli)
  * [2.2 Config DB](#22-config-db)
- [3 Design](#design)
  * [3.1 Login Limit Implementation](#31-login-limit-implementation)
  * [3.2 Default login session limitation Implementation](#32-default-login-session-limitation-Implementation)
  * [3.3 ConfigDB Schema](#33-configdb-schema)
  * [3.4 CLI](#34-cli)
- [4 Error handling](#error-handling)
- [5 Serviceability and Debug](#serviceability-and-debug)
- [6 Unit Test](#unit-test)
- [8 References](#references)


# About this Manual
This document provides a detailed description on the new features for:
 - Limit the number of logins per user/group/system.
 - Default limit user login session by device information.
 - Design a scalable framework of config command and ConfigDB to support more resource type, for example limit user CPU/memory by cgroup and systemd user.slices.

## SONiC memory issue sloved by this feature.
 - Currenly SONiC enabled OOM killer, and set 2 to /proc/sys/vm/panic_on_oom, which will trigger kernel panic when OOM. This is by design to protect SONiC key process and container.
 - A typical switch device have 4 GB memory and sonic usually will use 1.5 GB for dockers, and 500 MB for system process. so there will be 2 GB free memory for user. also sonic not enable swap for most device.
 - When user run some command trigger OOM, SONiC will kernel panic. for example:
   - Multiple user login to device, some service may create 10+ concurrent sesstion login to device.
   - Some user script/command take too much memory, currently 'show' command will take 60 MB memory.

# 1 Functional Requirement
## 1.1 Limit the login session per user/group/system
 - Can set max login session count per user/group/system.
 - When exceed maximum login count, login failed with error message.

## 1.2 Default limitation
- Default login session by device hardware and software information.
- For customer, they may have pipelines to initialize device configuration, because this feature add new commands, the pipeline may need update. The default limitation is designed to cover most case to minimize the customer side change.

# 2 Configuration and Management Requirements
## 2.1 SONiC CLI
 - Manage login session or memory  limit settings
```
    config limit login { enable | disable }
    config limit login { add | del } {user | group | global} <name> <number>
```
 - Show limit
```
    show limit login
```

## 2.2 Config DB
 - Login limit are fully configurable by config DB.

# 3 Design
 - Design diagram:

```mermaid
graph LR;
%% SONiC CLI update config DB
CLI[SONiC CLI] -- update limit setting --> CONFDB[(Config DB)];


%% HostCfgd subscribe config DB change
CONFDB -.-> HOSTCFGD[Hostcfgd];

%% HostCfgd Update config files
HOSTCFGD -- update limits.conf --> PAMCFG[limits.conf];

%% pam_limits.so will handle login limit
PAMCFG -.-> LIMITLIB[pam_limits.so];
LIMITLIB -- login --- USERSESSION(user session);

```

## 3.1 Login limit Implementation
 - Enable PAM plugin pam_limits.so to support login limit.
 - When login limit exceed, pam_limits.so will terminate login session with error message.

```mermaid
sequenceDiagram  

%% user login without exceed the limit
 SSH/Console->>SSHD  : login
	 activate  SSHD
	 SSHD->>pam_limits.so: check login limit
		 activate  pam_limits.so
		 pam_limits.so->>bash: not exceed the limit
			 activate  bash
			 bash->>SSH/Console: login success
			 deactivate  bash
	 SSH/Console->>SSHD  : logout
	 deactivate  SSHD
 
%% user login exceed the limit
 SSH/Console->>SSHD  : login
	 activate  SSHD
	 SSHD->>pam_limits.so: check login limit
		 activate  pam_limits.so
		 pam_limits.so->>SSH/Console: exceed the limit
		 deactivate  pam_limits.so
	 deactivate  SSHD
```
 #### Other solution for Linux login session limit

|                   | How                                                | Pros                                                         | Cons                       |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------------ | -------------------------- |
| PAM limit         | Change PAM setting file: /etc/security/limits.conf | Support per-user/per-group/global limit. Only need change config file. |                            |
| Bash login script | Call script when user login                        |                                                              | Need develop new script.   |
| SSHD config       | Change SSHD setting file: /etc/sshd_config         |                                                              | Only support global limit. |

- SONiC will create new user when domain user login, PAM limit support config limit to a not existed user.



## 3.2 Default login session limitation Implementation
- Global max login sessions: 10
- Max login sessions per-user: 3

## 3.3 ConfigDB Schema
 - Limit enable table:
```
; Key
limit_enable_key       = 1*32VCHAR         ; setting name, format is "limit_enable_" + resource type
; Attributes
resource_type          = LIST(1*32VCHAR)   ; Limit resource type, now only support (login)
enable                 = Boolean           ; Enable status, true for enable.
```

 - Limit setting table:
```
; Key
limit_key              = 1*32VCHAR         ; setting name, format is resource type + limit scope + limit name
; Attributes
resource_type          = LIST(1*32VCHAR)   ; Limit resource type, now only support (login)
scope                  = LIST(1*32VCHAR)   ; Limit scope, now only support (global, group, user)
value                  = Number  ; limit value, for login this is max login session count, for memory this is memory side in byte.
```
 - Yang model:
```
module sonic-system-limit {
	namespace "http://github.com/Azure/sonic-limit";
	prefix slimit;
	yang-version 1.1;

    revision 2022-01-12 {
        description "Initial revision.";
    }
    
    container sonic-system-limit {
        container limit {
            list limit_enable_list {
                key "limit_enable_key";

                leaf resource_type {
                    type enumeration {
                        enum login;
                    }
                    description "Resource type";
                }

                leaf enable {
                    type boolean;
                    description "Enable status";
                    default true;
                }
            }
            
            list limit_list {
                key "limit_key";

                leaf resource_type {
                    type enumeration {
                        enum login;
                    }
                    description "Resource type";
                }

                leaf scope {
                    type enumeration {
                        enum global;
                        enum group;
                        enum user;
                    }
                    description "Resource limit scope - global/group/user";
                }

                leaf value {
                    type uint64;
                    description "Limit value, for login this is max login session count.";
                    default 3;
                }
            }
        }
    }
}
```

## 3.4 CLI

 - Add following command to set/remove limit setting.
```
    // enable/disable login limit
    config limit login {enable | disable}
    
    // set global login limit
    config limit login add global <max session count>

    // remove global login limit
    config limit login del global

    // add group login limit
    config limit login add group <group name> <max session count>

    // remove group login limit
    config limit login del group <group name>

    // add user login limit
    config limit login add user <user name> <max session count>

    // remove user login limit
    config limit login del user <user name>
```

 - Add following command to show limit setting.
```
    // show login limit setting
    show limit login
```

# 4 Error handling
 - pam_limits.so will return errors as per [PAM](#pam) respectively.

# 5 Serviceability and Debug
 - pam_limits.so can be debugged by enabling the debug flag in PAM config file.

# 6 Unit Test

## 6.1 Login session enable/disable test

  - Enable login session limit and check the login session limit config updated correctly:
  ```
      Verify the config in /set/security/limits.conf updated correctly.
      Verify the device can't login when login session reach the max global login session count. 
      Verify the device can't login with same user count when login session reach the max per-user login session count. 
  ```

  - Disable login session limit and check the login session limit config updated correctly:
  ```
      Verify the config config command failed with warning message.
      Verify the device can login more login sessions coording to the max global login session count. 
      Verify the device can login with same user count when login session reach the max per-user login session count. 
  ```

## 6.2 Max login session test
  - Config global max login session count and check the login session limit config updated correctly:
  ```
      Verify the config in /set/security/limits.conf updated correctly.
      Verify the device can't login when login session reach the max global login session count. 
  ```

  - Config per-user max login session count and check the login session limit config updated correctly:
  ```
      Verify the config in /set/security/limits.conf updated correctly.
      Verify the device can't login with same user count when login session reach the max per-user login session count. 
  ```


# 7 References
## pam_limits.so
https://man7.org/linux/man-pages/man8/pam_limits.8.html

