# SONiC Filesystem support design spec draft

Table of Contents
<!-- TOC -->

- [SONiC Filesystem support design spec draft](##SONiC-Filesystem-support-design-spec-draft)
  - [Scope](#Scope)
  - [Document History](#Document-History)
  - [Abbreviations](#Abbreviations)
  - [SONiC Filesystem Feature Requirement](#SONiC-Filesystem-Feature-Requirement)
  - [Functionality](#Functionality)
    - [Target Deployment Use Cases](#Target-Deployment-Use-Cases)
    - [Functional Description](#Functional-Description)
  - [Dependencies](#Dependencies)
  - [SONiC system diagram for Filesystem](#SONiC-system-diagram-for-filesystem)
  - [The schema changes](#The-schema-changes)    
  - [Event flow diagram](#Event-flow-diagram)
  - [Modules changes](#Modules-changes)    
  - [CLI](#CLI)
  - [Other Linux utilities](#Other-Linux-utilities)
  - [User scenarios](#User-scenarios)    
  - [Test plan](#Test-plan)
<!-- /TOC -->
 
## Scope
This document describes the high-level design for the filesystem commands.

## Document History
| Version | Date       | Author       | Description                                      |
|---------|------------|--------------|--------------------------------------------------|
| v.01    | 08/04/2021 | Reemus Vincent, Syed Obaid Amin  | Initial version                      |


## Abbreviations
| **Term** | **Definition**                                                                                                                                  |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| URL      | Uniform Resource Locator  |

## SONiC Filesystem Feature Requirement
1. Add copy command to copy files from/to remote servers
2. Add dir command to list the files in the local storage
3. Add delete command to remove file from the local storage

### Functionality

#### Target Deployment Use Cases

The SONiC filesystem commands allow users to manage files in the SONiC Operating system. It provides several commands to help users manage configuration, support bundle, event-profile and core-dump files hence only folders containing these files and home folder are exposed to the users.

![image info](images/router-with-servers.jpg "Figure 1: Filesystem Deployment use case")
__Figure 1: Filesystem Deployment use case__

#### Functional Description
With this feature support, users will be able to:
  1. Take backup of System Configurations - both running and startup to any remote server
  2. Restore System Configuration from any remote server
  3. Copy Coredump files to any remote server
  4. Copy Support Bundle Files to any remote server
  5. Copy Event Profile from any remote server or local storage
  6. Copy Log Files to any remote server or local storage

## Dependencies
The Filesystem command depends on the following:
  1. D-Bus Service - reliable service communication channel between the Mgmt Framework Container and the Host Services (Host)
  2. "curl" utility for downloading files from remote server.

## SONiC system diagram for Filesystem
![image info](images/SONIC-Host-Service.jpg "Figure 3: Figure 2: SONiC Host Service")
__Figure 2: SONiC Host Service__

## The schema changes
Not applicable

## Event flow diagram
![image info](images/Filesystem-Eventflow.jpg "Figure 3: Figure 3: Event Flow Diagram")
__Figure 3: Event Flow Diagram__

## User Context
All the filesystem commands will have user context passed down from Xfmr to the Host Service. The "curl" utility will be run in the context of the user passed down to the Host Service.
The "home:" shortcut will be expanded to the appropriate home directory(/home/$USERNAME). The user will be able execute to dir/copy/delete filesystem commands on the the appropritate files/directories according to the user privilage and group. For "admin" role users, the commands will be executed with "sudo" utility.

All the "admin" role users will be added to "adm" group by default.

* Admin Role Users
  * Allowed to change running-configuration
  * Allowed to change startup-configuration
  * Allowed to  edit/delete files in home, config, coredump, event-profile & supportbundle - except log directory
  * Admin cannot delete syslog and should not be allowed to do so.
  * Allowed to take backup of the config, coredump, log, event-profile & supportbundle into their home directory
  * Allowed to take backup of the config, coredump, log, event-profile & supportbundle into remote server using ftp, scp & http
* Operator Role Users
  * Allowed write only to home directory from remote server
  * Allowed to write to remote server from home directory

## Module changes
* sonic-mgmt-common
  * YANG Model
  * Transformer
* sonic-mgmt-framework
  * CLI XML
  * Actioner
* sonic-host-service
  * Host Service

## CLI

### copy command
To copy a file from a source to a destination, use the copy <source-file-url> <destination-file-url>. 
The exact format of the source and destination URLs varies according to the file or directory location. 
Users may enter either a alias keyword for a particular file or a alias keyword for a file system type.

**Syntax:**
```
	copy <source-url> <destination-url>

```
Common Keyword Aliases for local files

| **Alias Name** | **Description**                                                                                                                      |
|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| startup-config | This alias represents the configuration file used during initialization (start up).  |
| running-config | This alias represents the current running configuration file. |
| config: | This alias represents the system config directory. |
| home: | This alias represents the $HOME directory of the current user. |
| coredump: | This alias represents the Coredump directory. |
| supportbundle: | This alias represents the Support Bundle directory. |
| logs: | This alias represents the log directory. |
| event-profile: | This alias represents the Event profile directory. |


URL Prefixes for Remote Files

| **Alias Name** | **Format**                                                             | **Description**                                                              |
|----------------|------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| ftp:           | ftp://[username [:password]@]{hostname\|host-ip}/directory/[filename]   | Source or destination URL of an FTP server. |
| http:          | http://[username [:password]@]{hostname\|host-ip}/directory/[filename]  | Source or destination URL of an HTTP server. |
| https:         | http://[username [:password]@]{hostname\|host-ip}/directory/[filename]  | Source or destination URL of an HTTPS server. |
| scp:           | scp://[username [:password]@]{hostname\|host-ip}/directory/[filename]    | Source or destination URL of an Secure Shell(SSH) server. |


**Note:**
Either the source or the destination should be a local file.

**Example**
```
sonic# copy ftp://admin:admin@10.10.10.10/new-startup-config.cfg startup-config
```

### dir command
List the files stored in available directories. The Dir command will list the files in the Filename-sorted order like Linux.

**Syntax:**
```
  dir [home: | coredump: | supportbundle: | logs: | config: | event-profile:]
```

### delete command
Remove or delete the file from the system.

**Syntax:**
```
  delete [home://<filename> | coredump://<filename> | supportbundle://<filename> | logs://<filename> | config://<filename> | event-profile://<filename>]
```

### Yang Model

**Copy Command**
```txt
  rpcs:
    +---x copy
    |  +---w input
    |  |  +---w source?        filename-uri-type
    |  |  +---w overwrite?     boolean
    |  |  +---w destination?   filename-uri-type
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
```

**Dir Command**
```txt
  rpcs:
  +--ro sonic-file-system-info
  |     +--ro system-folder* [name filename]
  |     |   +--ro name                  folder-name
  |     |   +--ro filename              string
  |     |   +--ro folder-match?         string
  |     |   +--ro file-size?            uint32
  |     |   +--ro last-modified-date?   yang:date-and-time
```

**Delete Command**
```txt
  rpcs:
  +---x delete-file
      |  +---w input
      |  |  +---w filename?   delete-filepath-type
      |  +--ro output
      |     +--ro status?          int32
      |     +--ro status-detail?   string
```

## Other Linux utilities
The filesystem will be using the "curl" utility to download and upload the files for remote files(ftp, http, scp & https).

## User scenarios

**User Scenario: 1**
```txt
! Backup Startup Configuration locally
sonic# copy startup-config home://config-backup-AUG0821
!!! copied successfully
sonic#
```

**User Scenario: 2**
```txt
! Backup Running Configuration locally
sonic# copy running-config home://config-backup-AUG0821
!!! copied successfully
sonic#
```

**User Scenario: 3**
```txt
! Backup Startup Configuration to a Remote FTP Server
sonic# copy startup-config ftp://admin:admin@10.10.10.10/startup-config-bkup
!!! copied successfully
sonic#
```

**User Scenario: 4**
```txt
! Backup Running Configuration to a Remote FTP Server
sonic# copy running-config ftp://admin:admin@10.10.10.10/config-bkup
!!! copied successfully
sonic#
```

**User Scenario: 5**
```txt
! Backup Running Configuration to a Remote SSH Server
sonic# copy running-config scp://admin:admin@10.10.10.10/config-bkup
!!! copied successfully
sonic#
```

**User Scenario: 6**
```txt
! Restore Running Configuration from a HTTP Server
sonic# copy http://inter128.acme.com/config-bkup running-config
!!! copied successfully
sonic#
```

**User Scenario: 7**
```txt
! Copy a Sonic Coredump file to FTP Server
sonic# copy coredump://sonic_dump_sonic_20210717_202813.tar.gz ftp://admin:admin@10.10.10.10/sonic_dump_sonic_20210717_202813.tar.gz
!!! copied successfully
sonic#
```

**User Scenario: 8**
```txt
! Display the contents of the config: 
sonic# dir home://
-------------------------------------------------------------------------
Date(Last Modified)      Size(Bytes)    Type      Filename
-------------------------------------------------------------------------
2021-11-02 13:02         19144          -         config_db.json
2021-11-02 13:01         30720          -         running-1.tar
2021-11-02 13:02         30720          -         running-2.tar
sonic#
```

**User Scenario: 9**
```txt
! Delete the config_backup.josn from home:
sonic# delete home://config_backup.josn
sonic#
```


## Test plan
* copy Command Testcases
  * source startup-config
    * verify CLI: copy startup-config running-config
    * verify CLI: copy startup-config home://...filename...
    * verify CLI: copy startup-config http://...filename...
    * verify CLI: copy startup-config ftp://...filename...
    * verify CLI: copy startup-config scp://...filename...
  * source running-config
    * verify CLI: copy running-config startup-config
    * verify CLI: copy running-config home://...filename...
    * verify CLI: copy running-config http://...filename...
    * verify CLI:copy running-config ftp://...filename...
    * verify CLI:copy running-config scp://...filename...
  * source home:
    * verify CLI: copy home://...filename... startup-config
    * verify CLI: copy home://...filename... running-config
    * verify CLI: copy home://...filename-1... home://...filename-2...
    * verify CLI: copy home://...filename... http://...filename...
    * verify CLI: copy home://...filename... ftp://...filename...
    * verify CLI: copy home://...filename... scp://...filename...
  * source coredump:
    * verify CLI: copy coredump://...filename... home://...filename...
    * verify CLI: copy coredump://...filename... http://...filename...
    * verify CLI: copy coredump://...filename... ftp://...filename...
    * verify CLI: copy coredump://...filename... scp://...filename...
  * source supportbundle:
    * verify CLI: copy supportbundle://...filename... home://...filename...
    * verify CLI: copy supportbundle://...filename... http://...filename...
    * verify CLI: copy supportbundle://...filename... ftp://...filename...
    * verify CLI: copy supportbundle://...filename... scp://...filename...
  * source logs:
    * verify CLI: copy logs://...filename... home://...filename...
    * verify CLI: copy logs://...filename... http://...filename...
    * verify CLI: copy logs://...filename... ftp://...filename...
    * verify CLI: copy logs://...filename... scp://...filename...
  * source event-profile:
    * verify CLI: copy event-profile://...filename... home://...filename...
    * verify CLI: copy event-profile://...filename... http://...filename...
    * verify CLI: copy event-profile://...filename... ftp://...filename...
    * verify CLI: copy event-profile://...filename... scp://...filename...
  * source http:
    * verify CLI: copy http://...filename... startup-config
    * verify CLI: copy http://...filename... running-config
    * verify CLI: copy http://...filename... home://...filename...
    * verify CLI: copy http://...filename... event-profile://...filename...
  * source ftp:
    * verify CLI: copy ftp://...filename... startup-config
    * verify CLI: copy ftp://...filename... running-config
    * verify CLI: copy ftp://...filename... home://...filename...
    * verify CLI: copy ftp://...filename... event-profile://...filename...
  * source scp:
    * verify CLI: copy scp://...filename... startup-config
    * verify CLI: copy scp://...filename... running-config
    * verify CLI: copy scp://...filename... home://...filename...
    * verify CLI: copy scp://...filename... event-profile://...filename...
  * Negative Testcases with source & destinations as Remote Servers
    * Unreachable Remote Server
    * Wrong Username for the Remote Server
    * Wrong Password for the Remote Server
    * Wrong Filename(not found) for the Remote Server
    * Wrong Filename(not found) locally (home:, logs:, event-profile:)
  * Managment VRF Testcases
    * Test the Remote File Testcases with Management VRF configured
  * Different Users
    * Test the commands with admin users
    * Test the commands with operator users
    * Test the commands with Radius/TACACS users
* dir Command Testcases
  * verify CLI: dir home:
  * verify CLI: dir home://...dirname...
  * verify CLI: dir config:
  * verify CLI: dir logs:
  * verify CLI: dir coredump:
  * verify CLI: dir supportbundle:
  * verify CLI: dir event-profile:
* delete Command Testcases
  * verify CLI: delete home:
  * verify CLI: delete home://...dirname...
  * verify CLI: delete config:
  * verify CLI: delete logs:
  * verify CLI: delete coredump:
  * verify CLI: delete supportbundle:
  * verify CLI: delete event-profile:


