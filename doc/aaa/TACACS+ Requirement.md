# SONiC TACACS+ Protocol Requirement

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

# About this Manual
This document provides a detailed description on the requirement of TACACS+ protocol support.

# 1 Functional Requirement
## 1.1 Authentication
- Authentication when user login to SONiC host.


## 1.2 Authorization
- Authorization when:
	- User login to SONiC host.
	- User run command on SONiC host.
		- User can only run commands in whitelist.
		- For recursive command/script, only the top level command have authorization.

- Only command in whitelist visible to user:
	- Whitelist is per host, all user share same whitelist to simplify design.
	- Different privilege level have different permission to run these command.
	- All commands in sudoers will add to the whitelist. and sudoers config file still need for RO users, this is because when remote TACACS server not accessible from SONiC, we need use local group permission for failover.

- Disable user behavior in shell:
	- Changing directories with the cd builtin.
		- User still can access files in other folder, and use 'ls' command to list content in other folder, for example:
	```
            test@testhost:~$ ls -l /etc/
            total 880
            drwxr-xr-x 3 test test       4096 Aug 22  2020 NetworkManager
            drwxr-xr-x 7 test test       4096 Aug 22  2020 X11
            drwxr-xr-x 3 test test       4096 Aug 22  2020 acpi
	```
	- Setting or unsetting the values of the SHELL, PATH, HISTFILE, ENV, or BASH_ENV variables.

	- Specifying command names containing slashes, for example:
	```
            test@testhost:~$ /etc/date
            rbash: /etc/date: restricted: cannot specify `/' in command names
	  
            test@testhost:~$ date
            Fri Jul  9 15:15:42 CST 2021
	```

	- Importing function definitions from the shell environment at startup.
	- Parsing the value of SHELLOPTS from the shell environment at startup.
	- Builtin commands:

| **Command** | **Behavior**                |
| -------- | -------------------------- |
| . | Specifying a filename containing a slash as an argument.     |
| history     | Specifying a filename containing a slash as an argument. |
| hash     | Specifying a filename containing a slash as an argument to the -p option. |
| exec     | Specifying a filename containing a slash as an argument to the -p option. |
| deleting/adding     | Use the -f and -d options to the enable builtin. |
| enable     | Using the 'enable' builtin command to enable disabled shell builtins. |
| command     | Specifying the -p option to the 'command' builtin command. |

	- All these behavior disabled only for user input, command in script will not be affected, see here for more details: https://www.gnu.org/software/bash/manual/html_node/The-Restricted-Shell.html


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
		- For recursive command/script, only the top level command have Accounting.
- Failover:
	- Use syslog as backup when remote TACACS not not accessible from SONiC.


## 1.4 User script
 - Any script in whitelist can run with Authorization and Accounting. 
 - If user create a script, admin user can use config command add script to whitelist.
 - To run user script, TACACS server side must allow user run script, for example:
	```
			1. Tacacs service allow RW user run any script named as 'user_script_*'
			2. RW user create a new script on sonic host, script name is 'user_script_collect_information.sh'
			3. Then user can add user_script_collect_information.sh to white list and run it. 
	```
## 1.5 Docker support
 - Docker exec command will be covered by Authorization and Accounting. 
 - SONiC AAA can't cover any command user run inside a docker.

## 1.6 Multiple TACACS server
 - Support config multiple TACACS server.
 - When a server not available, will try next server as backup.
 - When all server not accessible from SONiC, use native failover solution.

# 2 Configuration and Management Requirements
## 2.1 SONiC CLI
 - Enable/Disable TACACS Authorization/Accounting command
```
    config tacacs authorization enable
    config tacacs authorization disable
    config tacacs accounting enable
    config tacacs accounting disable
```

 - Whitelist management command
```
    show tacacs whitelist
    config tacacs whitelist remove <command>
    config tacacs whitelist add <command>
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

