# kdump_Remote_SSH

## High Level Design Document
**Rev 0.1**

## Table of Contents

<!-- TOC depthFrom:2 depthTo:4 withLinks:1 updateOnSave:1 orderedList:0 -->

- [High Level Design Document](#high-level-design-document)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
    - [Table 1: Abbreviations](#table-1-abbreviations)
- [Requirements Overview  <a name="requirements-overview"></a>](#requirements-overview-a-namerequirements-overviewa)
    - [Functional Requirements  <a name="functional-requirements"></a>](#functional-requirements-a-namefunctional-requirementsa)
    - [Scalability Requirements](#scalability-requirements)
    - [Warmboot Requirements](#warmboot-requirements)
    - [Configuration and Management Requirements](#configuration-and-management-requirements)
        - [Configuration commands](#configuration-commands)
	- [Information commands](#information-commands)
- [kdump : end-to-end flow](#kdump-end-to-end-flow)
- [Functional Description](#functional-description)
    - [Design](#design)
    - [Kernel core-dump service](#kernel-core-dump-service)
    - [SONiC Code Changes](#sonic-code-changes)
    - [Configuration commands:](#configuration-commands)
        - [config kdump <enable|disable>](#config-kdump-enabledisable)
        - [config kdump memory string](#config-kdump-memory-string)
        - [config kdump num_dumps number](#config-kdump-numdumps-number)
        - [show kdump [status]](#show-kdump-status)
        - [show kdump files](#show-kdump-files)
        - [show kdump log [X]](#show-kdump-log-x)
- [How to use the kernel core dump files](#how-to-use-the-kernel-core-dump-files)
    - [Introduction](#introduction)
    - [Use the kernel core dump file on the switch](#use-the-kernel-core-dump-file-on-the-switch)
    - [Use the kernel core dump file on a Linux host](#use-the-kernel-core-dump-file-on-a-linux-host)
    - [Analyzing the core dump](#analyzing-the-core-dump)
- [KDUMP DB](#kdump-db)
- [Test](#test)
    - [Test on Different Platforms](#test-on-different-platforms)
    - [Unit Test](#unit-test)

<!-- /TOC -->

## List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

## Revision

Rev   |   Date   |  Author   | Change Description
:---: | :-----:  | :------:  | :---------
0.1   | 06/05/2024 | Gulam Bahoo, Bilal Ismail | Initial version
## Overview
This document outlines the configuration and usage of the kdump remote feature with SSH for the SONiC network operating system. Kdump, a built-in Linux kernel feature, generates and stores a crash dump file in the event of a kernel panic. It extends beyond local storage by enabling remote dumps via SSH or NFS protocols, allowing you to transmit kernel crash data to a designated remote server. This functionality facilitates offline analysis by storing crash dump files remotely.

## Scope

This document describes how to configure remote kdump feature in SONiC infrastructure.

## Definitions/Abbreviations

### Table 1: Abbreviations

| **Term**     | **Meaning**            |
|  ----------- | ---------------------- |
| SSH          | Secure Shell           |
| kdump        | Kernel Dump            |
| NFS          | Network File System    |

## Requirements Overview  <a name="requirements-overview"></a>

### Functional Requirements  <a name="functional-requirements"></a>
This section describes the SONiC requirements for kdump remote feature.

At a high level the following should be supported:
1. The kernel core dump files must be stored on the a remote SSH server for offline analysis.
### Configuration and Management Requirements

- SONiC CLI support for configuring remote kdump feature enable/disable via SSH.
- SONiC CLI support for configuring username and hostname of SSH server (username@server_address).
- SONiC CLI support for configuring SSH private key path for SSH server (SSH_private_Key_Path).
- SONiC CLI support for displaying SSH crededentials of SSH server.
- SONiC CLI support for displaying SSH private key path for SSH server (SSH_private_Key_Path).
- SONiC CLI support for displaying state of kdump remote feature (enable/disable).
### SSH Key Generation Requirement
The system should authenticate with the remote server using SSH keys for secure access. 

```
ssh-keygen
```

You'll be prompted to choose a location to save the key pair. By default, it saves the private key to ~/.ssh/id_rsa and the public key to ~/.ssh/id_rsa.pub.

```
ssh-copy-id username@server_address
```

 This helps automate passwordless SSH logins by copying your public key to authorized servers.
### Warmboot Requirements

Configuring kdump feature always requires a cold reboot of the switch. Warmboot is not supported while generating a core file in the event of a kernel crash.



## kdump : Flow Control
![alt text](./images/kdump-ssh.drawio.png)

## Functional Description

### Design

The SONiC kernel core dump remote functionality can be divided into two categories:

1. Kernel core-dump generation service
2. Storing Kernel core-dump files remotely

## SONiC Code Changes

Current SONiC lacks remote kernel dump functionality. To add this feature, consider enabling kdump for remote storage.

### sonic-buildimage
1. build_debian.sh(Edit)
    - Required for kdump_remote_ssh_dump: Initialize network interfaces and enable DHCP upon kernel crash. Currently used on crash kernel boot only.

```
sudo cp files/scripts/network-interface-state-init.sh $FILESYSTEM_ROOT/usr/sbin/network-interface-state-init.sh
```
```
sudo chmod +x $FILESYSTEM_ROOT/usr/sbin/network-interface-state-init.sh
```

2. files/build_templates/sonic-debian-extension.j2(Edit)
    - Edit the kdump-tools package script to call a custom one, which shall enable ethernet interfaces in the crash kernel environment.
```
if [ -f "$FILESYSTEM_ROOT/usr/sbin/kdump-config" ]; then
    sudo sed -i "/PATH=\/bin:\/usr\/bin:\/sbin:\/usr\/sbin/a NET_INTERFACE_INIT=/usr/sbin/network-interface-state-init.sh" "$FILESYSTEM_ROOT/usr/sbin/kdump-config"
    sudo sed -i "/Network not reachable/a \\\t\t\t. \$NET_INTERFACE_INIT" "$FILESYSTEM_ROOT/usr/sbin/kdump-config"
fi
```

3. files/scripts/network-interface-state-init.sh (Addition)
```
#!/bin/sh

# Get list of Ethernet interfaces excluding Docker interfaces
interfaces=$(ip -o link show | awk -F': ' '$2 ~ /^e/ && $2 !~ /^docker/ {print $2}')

# Loop through each Ethernet interface
for interface in $interfaces; do
    # Check if the interface is already up
    if ! ip link show dev $interface | grep -q 'state UP'; then
        # Bring up the interface if it's not already up
        ip link set dev $interface up || { echo "Failed to bring up interface $interface"; continue; }
    fi

    # Configure the interface to use DHCP
    dhclient $interface || echo "Failed to configure DHCP for interface $interface"
done
```

## Configuration and management
This section describes all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below.



### KDUMP DB

 New attributes will be introduced to "KDUMP" table in ConfigDB for maintaining remote kdump configurations. Below is the schema for this table.

```
    KDUMP_TABLE:{{config}}
     "enabled"    :{{"false"|"true"}}
     "memory"     :{{string}}
     "num_dumps"  :{{number}}
     "remote"     :{{"false"|"true"}}
     "ssh_connection_string" :{{string}}
     "ssh_private_key_path" :{{string}}
```
### CLI Enhancements
#### Show CLI Commands
An existing SONiC CLI command is used to display the current remote kdump feature configuraitons.

```
show kdump config
```

Example output from the above command:
```
admin@sonic:~$ show kdump config
Kdump administrative mode: Enabled
Kdump operational mode: Ready
Kdump memory reservation: 512
Maximum number of Kdump files: 3
Kdump remote server user@ip/hostname: ghulam@172.16.7.13
Kdump private key file path for remote ssh connection: /home/admin/.ssh/id_rsa
```
## Test

### Unit Test Cases
- Enable/Disable remote kdump feature.
- Add/Remove SSH_Connection_String i.e. username@hostname.
- Add/Remove SSH_Private_Key_Path.

## Links
 - [White Paper: Red Hat Crash Utility](https://people.redhat.com/anderson/crash_whitepaper/)
 - [crash utility help pages](https://people.redhat.com/anderson/help.html)