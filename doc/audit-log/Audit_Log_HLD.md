# Feature Name
Audit Log.
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/16/2020  | Srinadh Penugonda  | Initial version                   |

# About this Manual
This document provides general information about the Audit Log feature implementation in SONiC.
# Scope
This document describes the high level design of Audit Log feature. 

# 1 Feature Overview

Audit log provides a way to monitor several security relevant information on the system with an insight on security health of the system.

## 1.1 Requirements

- The log messages will be stored as a separate file under /var/log on the switch itself and will follow similar format to syslog messages. No support for remote logging or remote destination.

- The audit log should contain the following messages:
  1. Log messages corresponding to login and logout through SSH and Console. The message content & format is from open source modules and is fixed.
  2. Log messages corresponding to when user tries config & show command via KLISH, gNMI and REST.  The command message will not have command hierarchy information.

  Audit log result for REST & gNMI will be in simple flat list; message will not be in key/value format.

- Log rotate is used to enforce size as 1M for audit log and goes through four rotations before being removed.

- Audit log files should be included in tech-support bundle.

### 1.1.2 Configuration and Management Requirements
- There need to be a show command to display the contents of audit log.
   1. show audit-log all - lists all messages from audit.log and rotated, uncompressed audit logs - namely, audit.log.1.
      The command will not attempt to display compressed and rotated audit log files.

      The *all* filter will fetch all audit log messages and potentially have performance implications and high response time.

   2. show audit-log     - lists recent 50 messages from audit.log

- There need to be a clear command to clear contents of audit logs.

## 1.2 Design Overview
### 1.2.1 Basic Approach
The feature implements the framework for audit log. As of now, the audit log comprises of messages corresponding to 
* login and logout related events through SSH and console 
* requests from north bound interfaces: CLI, REST and gNMI

Syslog rules are used to filter out these messages and populate audit log.

The login linux package is updated to trigger syslog message for login through console.

Any subsequent requirements to add new audit messages need to add a new syslog rule or augment existing syslog rules 
as mentioned in this [section](#311-syslog-rules)

# 2 Functionality
## 2.1 Target Deployment Use Cases
Audit Log collects certain types of system activity to facilitate incident investigation. The system activities includes
login/logout events through ssh/console. The other correpsonds to requests from north bound interfaces - CLI, REST and gNMI.

# 3 Design
## 3.1 Overview
Specified audit messages are stored in /var/log/audit.log.

Syslog rules with the help of various syslog properties like *syslogtag*, *syslogfacility*, *programname* are used to filter
these messages and redirect them to /var/log/audit.log.

SSHD triggers messages for login and logout through ssh. For login and logout through console, linux login package need to be
modified to trigger a syslog message.

Log rotate would manage audit log with size restrictions of 1M. 

### 3.1.1 Syslog Rules
SSHD generates successful login/logout messages with *authpriv* facility. Messages corresponding to invalid credentials triggered
with *auth* facility.

```
if $syslogtag contains 'sshd' then {
   if $syslogfacility-text == 'authpriv' then {
       action(type="omfile" file="/var/log/audit.log")
   }
   if $syslogfacility-text == 'auth' then {
       action(type="omfile" file="/var/log/audit.log")
   }
}
```
Management framework log messages are sent with *local4* facility.
```
if $syslogfacility-text == 'local4' then {
    action(type="omfile" file="/var/log/audit.log")
}
```
Some of the console login/logout messages comes through *systemd*.
```
if $programname == 'systemd' then {
    action(type="omfile" file="/var/log/audit.log")
}
```

The login linux package triggers messages corresponding to successful and failed login attempts with *programname* as **login**.
```
if $programname == 'login' then {
    action(type="omfile" file="/var/log/audit.log")
}
```

### 3.1.2 Linux login package
This package is modified to trigger a syslog message after user logs in. The build system is updated to build login target.

### 3.1.3 Commands
'show audit-log' displays contents of audit.log and audit.log.1. 
By default the command displays a brief snapshot of audit log by displaying around latest fity lines.
With *all* option, all of the audit.log and audit.log.1 is displayed.

Through REST, the path is /restconf/operations/sonic-auditlog:show-auditlog
For gNMI, the path is sonic-auditlog:show-auditlog

```
sonic# show audit-log
  <all>  Display all of audit log
  |      Pipe through a command
  <cr>
```
Through REST, the path is /restconf/operations/sonic-auditlog:clear-auditlog
For gNMI, the path is /sonic-auditlog:clear-auditlog

```
sonic# clear audit-log
  <cr>

```

### 3.1.4 Log rotate
Log rotate is configured to enforce size limitation of 1M for audit log. There will be four rotations. Rsyslog will be restated
after each rotation.

### 3.1.5 show tech-support
The existing show tech-support already packages all the files under /var/log into tech-support package.

Currently, the following log files from /var/log are packaged with tech support:
audit.log, auth.log, cron.log, daemon.log, messages, syslog, stpd.log, teamd.log, telemetry.log, udldd.log, user.log and zebra.log

## 3.2 User Interface
### 3.2.1 Data Models
```
module sonic-auditlog {
    namespace "http://github.com/Azure/sonic-auditlog";
    prefix auditshow;
    yang-version 1.1;

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONiC yang for RPC based show/clear audit log.";

    revision 2020-05-29 {
        description
            "Initial revision.";
    }

    rpc show-auditlog {
       description "RPC for showing audit log.";

       input {
           leaf content-type {
               type string {
                   pattern "all";
               }
               description "Indicates if user wants to display all of audit log";
           }
       }

       output {
           leaf audit-content {
               type string;
               description "Content of audit log as per input content type";
           }
       }
    }

    rpc clear-auditlog {
       description "RPC for clearing audit log.";
    }
}

```
### 3.2.2 CLI
#### 3.2.2.1 Configuration Commands
Clearing audit log is implemented as RPC and is achieved with the help of HostQuery module - clearaudit.py. 
On receiving the request from container, this module will remove audit.log and restarts rsyslog.

```
sonic# clear audit-log
sonic#
```

#### 3.2.2.2 Show Commands
To display contents of audit log, show command is implemented and it is RPC.
To achieve better performance, audit log is mounted onto mgmt-framework container.
The command by default displays a brief snapshot of audit log by showing last fifty lines.
The command has an 'all' option to display all of the audit.log and audit.log.1.

```
sonic# show audit-log
  <all>  Display all of audit log
  |      Pipe through a command
  <cr>
```

### 3.2.3 REST API Support
#### 3.2.3.1 Show Audit Log 
Path: /restconf/operations/sonic-auditlog:show-auditlog

Input: "all" or none

#### 3.2.3.2 Clear Audit Log 
Path: /restconf/operations/sonic-auditlog:clear-auditlog

### 3.2.4 GNMI API Support
#### 3.2.4.1 Show Audit Log 
Path: /sonic-auditlog:show-auditlog

Input: "all" or none

#### 3.2.4.2 Clear Audit Log 
Path: /sonic-auditlog:clear-auditlog

# 4 Serviceability and Debug

- **Successful login**

Provides user name, IP from where user is logging in from.

*SSH*

Jun 2 22:47:08.619590 sonic INFO sshd[13990]: Accepted password for **admin** from **10.14.8.140** port 49074 ssh2
Jun 2 22:47:08.711691 sonic INFO sshd[13990]: pam_unix(sshd:session): **session opened** for user **admin** by (uid=0)

The first message displays that authentication was successful for the user 'admin'. The IP of the host from where host is trying to login is displayed along with its port. 

Timestamp at which the login occurred is displayed.

The subsequent log indicates that session has been opened for user 'admin'.

*Console*

Jun 2 22:48:47.939333 sonic INFO login[30983]: Accepted password for **admin** on terminal=**'/dev/ttyS0'**
Jun 2 22:48:48.056522 sonic INFO login[30983]: pam_unix(login:session): **session opened** for user **admin** by LOGIN(uid=0)

- **Successful logout**

Provides user name, IP from where user is logging out from.

*SSH*

Jun 2 22:49:33.855434 sonic INFO sshd[14073]: Received disconnect from **10.14.8.140** port 49074:11: **disconnected by user**
Jun 2 22:49:33.966591 sonic INFO sshd[13990]: pam_unix(sshd:session): **session closed** for user **admin**

The first message indicates that user has disconnected the session. The IP and port of the host from which user disconnected the session is displayed as well.

The second message indicates that session for user 'admin' has been closed.

Timestamp at which the login occurred is displayed.

*Console*

Jun 2 22:50:47.510380 sonic INFO login[30983]: pam_unix(login:session): **session closed** for user **admin**
Jun 2 22:50:47.665222 sonic INFO systemd[1]: Stopped Serial Getty on **ttyS0**

- **Login with invalid username**

Provides invalid user name and IP address of the host invalid user is trying to log in from.

*SSH*

Jun 2 22:51:53.619712 sonic INFO sshd[31688]: **Invalid user** **adminxxx** from **10.14.8.140** port 49090

The message indicates that there was an attempt to connect over ssh with an invalid user name. 

The user name is displayed along with the host IP and port from which user tried to login.

*Console*

Jun 2 22:52:49.080189 sonic NOTICE login[27921]: pam_unix(login:auth): **authentication failure**; logname=LOGIN uid=0 euid=0 **tty=/dev/ttyS0** ruser= rhost=
Jun 2 22:52:52.055801 sonic NOTICE login[27921]: FAILED LOGIN (1) on '/dev/ttyS0' FOR 'UNKNOWN', Authentication failure

- **Login with invalid password**

Informs that specified user trying to log in with an invalid password and informs IP of the host user is logging in from.

*SSH*

Jun 2 22:53:39.571670 sonic NOTICE sshd[6296]: pam_unix(sshd:auth): **authentication failure**; logname= uid=0 euid=0 tty=ssh ruser= rhost=**10.14.8.140** user=**admin**
Jun 2 22:53:41.163938 sonic INFO sshd[6296]: Failed password for admin from 10.14.8.140 port 49094 ssh2

The message indicates that user 'admin' entered wrong password that resulted in authentication failure. 

The host IP and port from which user tried the login is displayed in the message.

*Console*

Jun 2 22:54:54.938982 sonic NOTICE login[6927]: pam_unix(login:auth): **authentication failure**; logname=LOGIN uid=0 euid=0 **tty=/dev/ttyS0** ruser= rhost= user=**admin**
Jun 2 22:54:57.568058 sonic NOTICE login[6927]: FAILED LOGIN (1) on '/dev/ttyS0' FOR 'admin', Authentication failure

- **Session Timeout**

*SSH*
Jun 10 19:26:32.887528 sonic INFO sshd[24578]: **Timeout, client not responding.**

Jun 10 19:26:33.025597 sonic INFO sshd[24481]: pam_unix(sshd:session): **session closed** for user **admin**

*Console*

Jun 10 20:02:33.904878 sonic INFO systemd[1]: **Stopped Serial Getty** on **ttyS0**.

- **Set Request**

Informs type of request, URI, user name, command string and status of command execution.

*CLI*

Jun 2 22:57:09.060819 sonic INFO mgmt-framework#clish: User "**admin**" command "**tacacs-server key mykey**"  status - **success**

The message displays the command string; its status and name of the user that executed the command.

*REST/gNMI*

Jun 12 19:33:40.728039 sonic INFO mgmt-framework#/usr/sbin/rest_server[711]: [REST-5] User "**admin@10.14.125.28**:55937" request "**PATCH** **/restconf/data/openconfig-system:system/aaa/server-groups/server-group=TACACS/config/openconfig-system-ext:secret-key**" status - **204**

- **Delete Request**

Informs type of request, URI, user name, command string and status of command execution.

*CLI*

May 27 21:19:32.141471 sonic INFO mgmt-framework#clish: User "**admin**" command "**no tacacs-server timeout**" status - **success**

The message displays the command string; its status and name of the user that executed the command.

*REST/gNMI*

Jun 12 19:35:03.326971 sonic INFO mgmt-framework#/usr/sbin/rest_server[711]: [REST-6] User "**admin@10.14.125.28**:55937" request "**DELETE /restconf/data/openconfig-system:system/aaa/server-groups/server-group=TACACS/config/openconfig-system-ext:secret-key**" status - **204**

- **Get Request**

Informs type of request, URI, user name, command string and status of command execution.

*CLI*

Jun 2 22:55:55.171404 sonic INFO mgmt-framework#clish: User "**admin**" command "**show tacacs-server global**" status - **success**

The message displays the command string; its status and name of the user that executed the command.

*REST/gNMI*

Jun 12 19:36:04.059130 sonic INFO mgmt-framework#/usr/sbin/rest_server[711]: [REST-7] User "**admin@10.14.125.28**:55937" request "**GET /restconf/data/openconfig-system:system/aaa/server-groups/server-group=TACACS/config/openconfig-system-ext:secret-key**" status - **200**

# 5 Unit Test
- show audit-log : Should display around last fifty audit messages (this is not hardcoded rather approximate number as go doesnt offer parsing files through lines)
- show audit-log all : Should display audit.log and audit.log.1 (if it exists)
- clear audit-log : clears audit-log
- Login through ssh, verify that show audit-log displays messages corresponding to login
- Logout through ssh, verify that show audit-log displays messages corresponding to logout
- Login through console, verify that show audit-log displays messages corresponding to login
- Logout through console, verify that show audit-log displays messages corresponding to logout
- Login with invalid password through ssh, verify that show audit-log displays messages corresponding to login
- Login with invalid password through console, verify that show audit-log displays messages corresponding to login
- Login with invalid username through ssh, verify that show audit-log displays messages corresponding to login
- Login with invalid username through console, verify that show audit-log displays messages corresponding to login
- timeout for an existing ssh session, verify that show audit-log displays messages corresponding to session clearing out
- timeout for an existing console session, verify that show audit-log displays messages corresponding to session clearing out
- set request through CLI, REST, gNMI, verify show audit-log displays user, command string (for CLI) / path (for REST/gNMI) and status
- get request through CLI, REST, gNMI, verify show audit-log displays user, command string (for CLI) / path (for REST/gNMI) and status
- delete request through CLI, REST, gNMI, verify show audit-log displays user, command string (for CLI) / path (for REST/gNMI) and status
- Verify that show tech-support has audit log packaged
