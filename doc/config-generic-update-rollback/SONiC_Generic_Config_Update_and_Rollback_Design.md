# SONiC Generic Configuration Update and Rollback

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definition-abbreviation)
    + [Table 1: Abbreviations](#table-1--abbreviations)
- [1 Feature Overview](#1-feature-overview)
  * [1.1 Requirements](#11-requirements)
    + [1.1.1 Functional Requirements](#111-functional-requirements)
    + [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
    + [1.1.3 Scalability Requirements](#113-scalability-requirements)
    + [1.1.4 Warm Boot Requirements](#114-warm-boot-requirements)
  * [1.2 Design Overview](#12-design-overview)
    + [1.2.1 Basic Approach](#121-basic-approach)
    + [1.2.2 Container](#122-container)
- [2 Functionality](#2-functionality)
  * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [2.2 Functional Description](#22-functional-description)
    + [2.2.1 Apply-Patch](#221-apply-patch)
      - [Stage-1 Patch Ordering](#stage-1-patch-ordering)
      - [Stage-2 Identifying Services to Restart](#stage-2-identifying-services-to-restart)
      - [Stage-3 Add delay after table updates for listening services to absorb changes](#stage-3-add-delay-after-table-updates-for-listening-services-to-absorb-changes)
      - [Stage-4 Apply patch, service restarts and delays](#stage-4-apply-patch--service-restarts-and-delays)
      - [Stage-5 Verify patch update](#stage-5-verify-patch-update)
      - [Fail-safe Action](#fail-safe-action)
      - [Logging](#logging)
    + [2.2.2 Checkpoint](#222-checkpoint)
      - [Stage-1 Get current ConfigDB JSON config](#stage-1-get-current-configdb-json-config)
      - [Stage-2 Save JSON config](#stage-2-save-json-config)
    + [2.2.3 rollback](#223-rollback)
      - [Stage-1 Get current ConfigDB JSON config](#stage-1-get-current-configdb-json-config-1)
      - [Stage-2 Get checkpoint JSON config](#stage-2-get-checkpoint-json-config)
      - [Stage-3 Generate the diff as JsonPatch between current config and checkpoint](#stage-3-generate-the-diff-as-jsonpatch-between-current-config-and-checkpoint)
      - [Stage-4 Apply-Patch](#stage-4-apply-patch)
      - [Stage-5 Verify config rollback](#stage-5-verify-config-rollback)
      - [Fail-safe Action](#fail-safe-action-1)
      - [Logging](#logging-1)
- [3 Design](#3-design)
  * [3.1 Overview](#31-overview)
    + [3.1.1 ApplyPatch](#311-applypatch)
    + [3.6 User Interface](#36-user-interface)
    + [3.6.1 Data Models](#361-data-models)
      - [3.6.1.1 JsonPatch](#3611-jsonpatch)
      - [3.6.1.2 ApplyPatch Metadata](#3612-applypatch-metadata)
    + [3.6.2 CLI](#362-cli)
      - [3.6.2.1 Configuration Commands](#3621-configuration-commands)
      - [3.6.2.2 Show Commands](#3622-show-commands)
      - [3.6.2.3 Debug Commands](#3623-debug-commands)
- [4 Flow Diagrams](#4-flow-diagrams)
- [5 Error Handling](#5-error-handling)
- [6 Serviceability and Debug](#6-serviceability-and-debug)
- [7 Warm Boot Support](#7-warm-boot-support)
- [8 Scalability](#8-scalability)
- [9 Unit Tests](#9-unit-tests)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)


# Revision

| Rev |     Date    |       Author       | Change Description  |
|:---:|:-----------:|:------------------:|---------------------|
| 0.1  | 01/12/2021 | Mohamed Ghoneim    | Initial version     |

# About this Manual
This document provides a detailed description on the strategy to implement the SONiC configuration generic update and rollback feature.

# Scope
This document describes the high level design of a SONiC configuration generic update and rollback feature. This document provides minor implementation details about the proposed solutions.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term** | **Meaning**                |
| -------- | -------------------------- |
| ConfigDB | Configuration Database     |
| JSON     | JavaScript Object Notation |

# 1 Feature Overview

Updating SONiC partial configurations **systematically** has been a challenge for a long time, as each part of the config has different requirements in terms of which files to push to the device, what commands to use, and if there are services that need manual restarting. For example updating `ACLs` is very different from updating `DHCP` configurations.

*ACLs*: Updating ACLs require the following steps:
- Pushing `acl.json` file to the device that contain the new ACL rules
- Pushing `minigraph.xml` to the device that contains the new ACL interfaces
- Execute `sudo acl-loader update full /etc/sonic/acl.json --table_name example_acl`

*DHCP*: Updating DHCP config requires the following steps:
- Pushing `minigraph.xml` to the device that contains the new ACL interfaces
- Generating `dhcp_servers` JSON configs from the `minigraph.xml`, and saving it a temporary file
- Executing `sudo sonic-cfggen -j /tmp/dhcp.json --write-to-db`
- Restart `dhcp_relay` service

We have explored [SONiC CLI commands](https://github.com/Azure/sonic-utilities/blob/master/doc/Command-Reference.md) to make configuration changes. These CLI commands result in updates to the ConfigDB which are corresponding to the CLI command executed. For example, the config `vlan add 10` will create a new row in the VLAN table of the ConfigDB. But relying on the CLI commands to do partial update is also not feasable as there is no standard way of showing the config after the update. Setting up a different update mechanism for each part of the config is very time consuming and ineffecient.

The other challenge to updating a switch is recoverability via rollback. Rollback needs to be hitless/non-disruptive e.g. if reverting ACL updates DHCP should not be affected. Currently SONiC has a couple of operations that can be candidates for rollback `config load` and `config reload`.

*config reload <config_db.json>* : This command clears all the contents of the ConfigDB and loads the contents of config_db.json into the ConfigDB. After that all the Docker containers  and Linux services are restarted to establish the user specified configuration state in the config_db.json file.

- Pro's
  - Assured way of affecting a configuration state change
- Con's
  - Brings the links down and resets the forwarding state. This operation is disruptive in nature
  - Time consuming as it may take 2-3 minutes for all the services to come back online. The time taken may vary based on the switch CPU power.
- Verdict
  - Cannot be used as a rollback mechanism

*config load  <config_db.json>*: This command loads the contents of config_db.json into the ConfigDB. The updates made to the ConfigDB are additive in nature and thus the new configuration state is a combination of the current running state and the partial configuration state specified by the user in the config_db.json file

- Pro's
  - Quick way to add new configuration changes
  - It does not disrupt existing service whose configuration is not being modified. So it is non-disruptive in nature
- Con's
  - Can't remove existing configuration and can only be used to add/modify the existing configuration
- Verdict
  - Cannot be used as a rollback mechanism

Since both `config load` and `config reload` are not suitable for a hitless/non-disruptive rollback, we have to look for other approaches.

In this design document, we will be exploring how to standardize the way to do partial updates, how to take checkpoints and finally how to rollback the configurations.

In summary, this is the flow of an update:

![basic-target-design](files/basic-target-design.png)

And the steps would be:
```
admin@sonic:~$ checkpoint mycheckpoint
admin@sonic:~$ echo "config changes to apply to ConfigDb" > some-config-changes.patch
admin@sonic:~$ apply-patch ./some-config-changes.patch
admin@sonic:~$ rollback mycheckpoint # in case of failures
```

## 1.1 Requirements

### 1.1.1 Functional Requirements
- A single, simple command to partially update SONiC configuration according to a patch of updates
- A single, simple command to take a checkpoint of the full current SONiC config
- A single, simple command to fully rollback current SONiC configs with to a checkpoint
- Other commands to list checkpoints, delete checkpoints
- The patch of updates should follow a standard notation. The [JSON Patch (RFC6902)](https://tools.ietf.org/html/rfc6902) notation should be used
- Config rollback should be with minimum disruption to the device e.g. if reverting ACL updates DHCP should not be affected i.e. hitless rollback
- User should be able to preview the configuration difference before going ahead and committing the configuration changes
- In case of errors, the system should just report an error and the user should take care of it
- Only 1 user session can update device config at a time i.e. no concurrent updates to configurations

### 1.1.2 Configuration and Management Requirements
- All commands should support KLISH CLI style
- All commands argument to generated using Python-click to provide help menus and other out-of-the box features
- Only root user must be allowed to execute the commands
- Each command must provide the following sub options:
  - "dry-run" Perform a dry-run of the command showing exactly what will be executed on the device, without executing it
  - "verbose" Provide additional information on the steps executed

### 1.1.3 Scalability Requirements
N/A

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview

### 1.2.1 Basic Approach
SONiC ConfigDB contents can be retrieved in a JSON file format. Modifying JSON file should follow some rules in order to make it straightforward for the users. Fortunately there is already a formal way of defning JSON config updates. It is called JsonPatch, and is formally defined in [RFC 6902 JSON Patch](https://tools.ietf.org/html/rfc6902).

On top of ConfigDBConnector in `sonic-py-swssdk` we are going to implement [RFC 6902 JSON Patch](https://tools.ietf.org/html/rfc6902). This API we will call `apply-patch`. On top of that API, we will implement the `rollback` functionality. It will simply starts by getting the diff (patch) between the checkpoint and the current running config, then it will call the API `apply-config` to update that patch.

The [JsonPatch](https://pypi.org/project/jsonpatch/) python is an open source library that already implements the [RFC 6902 JSON Patch](https://tools.ietf.org/html/rfc6902). We can leverage this library to verify patch config, generate a diff between checkpoint and current running config, verify apply-patch and rollback work as expected by simulating the final output of the update and comparing with the observed output.

**Example:**
Assume running-config to be:
```
{
  "DEVICE_NEIGHBOR": {
    "Ethernet8": {
      "name": "Servers1",
      "port": "eth0"
    },
    "Ethernet96": {
      "name": "Servers23",
      "port": "eth0"
    },
  },
  "DHCP_SERVERS": {
    "1.1.1.1": {},
    "2.2.2.2": {},
    "3.3.3.3": {}
  }
}
```

and the ask to:
- replace *port* under *Ethernet8* with *eth1*
- add 4.4.4.4 tanother DHCP_SERVER with IP 
- remove 2.2.2.2 from DHCP_SERVERS

The steps would be:

1) Take a checkpoint of the config
```
admin@sonic:~$ checkpoint mycheckpoint
```
2) Create a file on the device named `dhcp-changes.patch.json`, with the following content
```
[
  {
    "op": "replace",
    "path": "/DEVICE_NEIGHBOR/Ethernet8/port",
    "value": "eth1"
  },
  {
    "op": "add",
    "path": "/DHCP_SERVERS/4.4.4.4,",remove
    "path": "/DHCP_SERVERS/2.2.2.2"
  },
]
```
3) Apply patch using `apply-patch` command
```
admin@sonic:~$ apply-patch ./dhcp-changes.patch.json
```
4) In case of failure, rollback the config using `rollback` command
```
admin@sonic:~$ rollback mycheckpoint --verbose # verbose to see generated patch
```
This will internally do a diff, and generate patch of the needed changes and apply using `apply-patch`.
The patch will be:
```
[
  {
    "op": "replace",
    "path": "/DEVICE_NEIGHBOR/Ethernet8/port",
    "value": "eth0"
  },
  {
    "op": "remove",
    "path": "/DHCP_SERVERS/4.4.4.4,",
    "value": {}
  },
  {
    "op": "add",
    "path": "/DHCP_SERVERS/2.2.2.2"
  },
]
```

### 1.2.2 Container

All the introduced commands will be part of the *python-sonic-utilities* package installed in Debian host O/S.

# 2 Functionality

## 2.1 Target Deployment Use Cases

The `apply-patch` method should help with automating partial config updates, as external systems can generate the update patch, and apply.

The `checkpoint` and `rollback` commands should help improve recoverability, can also be used by external systems to help revert failures during `apply-patch` operation.

Human operators can also leverage the `checkpoint` and `rollback` functionalities while doing updates through the CLI using [SONiC CLI commands](https://github.com/Azure/sonic-utilities/blob/master/doc/Command-Reference.md).

## 2.2 Functional Description

### 2.2.1 Apply-Patch
The SONiC `apply-patch` command can broadly classified into the following steps

#### Stage-1 Patch Ordering
As per the JSON standard, the elements described in JSON format are unordered. However, in SONiC there are some tables which can not be processed before another table is updated. For example changes to the VLAN_MEMBER table needs to be processed before the PORTCHANNEL table is processed. If the ordering is not established, the Port Channel delete operation will fail with an error message complaining that the port-channel is still part of a VLAN. So it is essential that the dependency between the tables is identified and the patch is processed in that order.

The `apply-patch` command uses an ordering table which specifies the list of dependent tables that need to be processed before a table is processed. Below is an example depiction of two ConfigDB tables.

```
{
  "VLAN" : ["VLAN_MEMBER", "VLAN_INTERFACE"],
  "PORTCHANNEL" : ["VLAN_MEMBERSHIP", "PORTCHANNEL_MEMBER"]
}
```
A dependency graph is created for all the tables which are in the JSON patch file. The dependency graph is then resolved to find the order in which the updates to tables in the JSON patch are performed. The JSON patch file is then sorted in the resolved order.

#### Stage-2 Identifying Services to Restart
There are a few SONiC applications which store its configuration in the ConfigDB. These applications do not subscribe to the ConfigDB change events. So any changes to their corresponding table entries as part of the patch apply process in the ConfigDB are not processed by the application immediately. In order to apply the configuration changes, corresponding service needs to be restarted. A list of such ConfigDB tables and corresponding systemd service is specified in the *apply-patch* command.  See below for an example.

```
{
  "SYSLOG_SERVER": ["rsyslog"],
  "DHCP_SERVER": ["dhcp_relay"],
  "NTP_SERVER": ["ntp-config.service", "ntp.service"]
  "BGP_MONITORS": ["bgp"],
  "BUFFER_PROFILE": ["swss"],
  "RESTAPI": ["restapi"]
}
```

This table is used to restart corresponding systemd service when a patch operation has been perform on its corresponding ConfigDB table. 

#### Stage-3 Add delay after table updates for listening services to absorb changes
Will divide the patch into groupings by table. After updating each table, we will introduce an artificial sleep to give a pause between two table updates as to ensure that all internal daemons have digested the previous update, before the next one arrives.

#### Stage-4 Apply patch, service restarts and delays
At this stage we have built all the steps needed. The steps include JsonPatch operations, restart operations and delay operations.

The JsonPatch consistes of a list operation, and the operation follows this format:
```
  { "op": "<Operation-Code>", "path": "<Path>", "value": "<Value>", "from": "<From-Path>" }
```
For detailed information about the JSON patch operations refer to the  section 4(Operations) of [RFC 6902](https://tools.ietf.org/html/rfc6902).



**Operation Code**

- replace - Set ConfigDB entry described in Path to be equal to the data specified in Value

- add - Create a new ConfigDB entry described in Path and set it Value

- remove - Delete the ConfigDB entry described in Path

- copy - Copy the ConfigDB entry  specified in the FromPath to create a ConfigDB entry specified in Path
- move - Copy the ConfigDB entry specified in the FromPath to create a ConfigDB entry specified in Path and then delete the ConfigDB entry in FromPath



**Path**

Describes the location of the ConfigDB entry which is being processed. The path string can be dissected into below elements.

- Table Name - The ConfigDB table corresponding to the entry
- Key - The Key string to identify the row data within the ConfigDB table
- Field - The column_key to identify the ConfigDB entry within the identified row data

e.g  "/VLAN_MEMBER/Vlan10|Ethernet0/tagging_mode"

- Table: VLAN_MEMBER
- Key: Vlan10|Ethernet0
- Field: tagging_mode


**FromPath**

- Same as Path used in copy and move operations



**Value**

- Data that is used to patch the ConfigDB entry specified in path

#### Stage-5 Verify patch update
The expectations after applying the JsonPatch is that it will adhere to [RFC 6902](https://tools.ietf.org/html/rfc6902).

The verficiation steps
1) Get the state of ConfigDB JSON before the update as a JSON object
2) Simulate the JsonPatch application over this JSON object
3) Compare that JSON object with current ConfigDB JSON
4) In case of mismatch, just report failure

#### Fail-safe Action

If an error is encountered during the `apply-patch` operation, an error is reported and the system DOES NOT take any automatic action. The user can take a `checkpoint` before running `apply-patch` and if the operation failed, the user can `rollback`. Another idea is to introduce a `config-session` where a user enters a `config-session` mode does all the modifications, once they are happy with it, they `commit` the changes to ConfigDB. `config-sesion` can be built using `checkpoint` and `rollback` functionality, but this `config-session` idea is beyond the scope of this document.

#### Logging

All the configuration update operations executed and the output displayed by the `apply-patch` command are stored in the systemd journal. They are also forwarded to the syslog. By storing the commands in the systemd-journal, the user will be able to search and display them easily at a later point in time. The `show apply-patch log` command reads the systemd-journal to display information about the `apply-patch` command that was previously executed or currently in progress.

### 2.2.2 Checkpoint
The SONiC `checkpoint` command can broadly classified into the following steps

#### Stage-1 Get current ConfigDB JSON config
The  *ConfigDBConnector* class of the *sonic-py-swsssdk* is used to obtain the running configuration in JSON format

#### Stage-2 Save JSON config
Save the checkpoint to a dedicted loction on the SONiC box

### 2.2.3 rollback
The SONiC `rollback` command can broadly classified into the following steps

#### Stage-1 Get current ConfigDB JSON config
The  *ConfigDBConnector* class of the *sonic-py-swsssdk* is used to obtain the running configuration in JSON format

#### Stage-2 Get checkpoint JSON config
Load the checkpoint from the SONiC box

#### Stage-3 Generate the diff as JsonPatch between current config and checkpoint
The current ConfigDB JSON config is compared with the JSON config from the checkpoint. The comparison result should be in JsonPatch format.

#### Stage-4 Apply-Patch
Pass the generated JsonPatch to the apply-patch API

#### Stage-5 Verify config rollback
Compare the ConfigDB JSON after the update with the checkpoint JSON, there should be no differences.

#### Fail-safe Action

If an error is encountered during the `rollback` operation, an error is reported and the system DOES NOT take any automatic action. Rollback operation is itself an automated fail-safe action, if itself fails the caller should decide how to handle such failures e.g. generate an alert of high severity, or do `config reload`.

#### Logging

All the configuration update operations executed and the output displayed by the `rollback` command are stored in the systemd journal. They are also forwarded to the syslog. By storing the commands in the systemd-journal, the user will be able to search and display them easily at a later point in time. The `show rollback log` command reads the systemd-journal to display information about the `rollback` command that was previously executed or currently in progress.

# 3 Design

## 3.1 Overview

### 3.1.1 ApplyPatch
![apply-patch-design](files/apply-patch-design.png)

### 3.6 User Interface

### 3.6.1 Data Models

#### 3.6.1.1 JsonPatch

The JsonPatch consistes of a list operation, and each operation follows this format:
```
  { "op": "<Operation-Code>", "path": "<Path>", "value": "<Value>", "from": "<From-Path>" }
```
For detailed information about the JSON patch operations refer to the  section 4(Operations) of [RFC 6902](https://tools.ietf.org/html/rfc6902).



**Operation Code**

- replace - Set ConfigDB entry described in Path to be equal to the data specified in Value

- add - Create a new ConfigDB entry described in Path and set it Value

- remove - Delete the ConfigDB entry described in Path

- copy - Copy the ConfigDB entry  specified in the FromPath to create a ConfigDB entry specified in Path
- move - Copy the ConfigDB entry specified in the FromPath to create a ConfigDB entry specified in Path and then delete the ConfigDB entry in FromPath



**Path**

Describes the location of the ConfigDB entry which is being processed. The path string can be dissected into below elements.

- Table Name - The ConfigDB table corresponding to the entry
- Key - The Key string to identify the row data within the ConfigDB table
- Field - The column_key to identify the ConfigDB entry within the identified row data

e.g  "/VLAN_MEMBER/Vlan10|Ethernet0/tagging_mode"

- Table: VLAN_MEMBER
- Key: Vlan10|Ethernet0
- Field: tagging_mode


**FromPath**

- Same as Path used in copy and move operations



**Value**

- Data that is used to patch the ConfigDB entry specified in path
#### 3.6.1.2 ApplyPatch Metadata

A new file will be added to the system which will contain the `apply-patch` metadata.

The format of the file would be:
```
{
  "tables: {
    "<TABLE-NAME>": {
      "upstream-tables": ["<TABLE1>, "<TABLE2>" ...],
      "services-to-restart": ["<SERVICE1>", "<SERVICE2>" ...],
    },
    .
    .
    .
  },
  "default-delay-between-table-updates": <INTEGER>
}
```

The document contain info describing the dependency graph of tables (i.e. the topology), services associated with table, and also the delay duration between different tables updates. The granuality is based on the table, as using just the table names we can re-order, and generate all the need operations

- tables - contains the all the information need for the tables
- TABLE-NAME - The table name correspndong to atables from ConfigDB, will contain all the tables metadata. There can be multiple different TABLE-NAME keys/dictionaries.
- upstream-tables - The list of all tables that need to be updated first before current table. There can be multiple upstream tables.
- services-to-restart - The list of services to restart after updating the current table. There can be multiple services to restart.
- default-delay-between-table-updates - Some daemons are listening to ConfigDB changes, so artificial sleep to give a pause between two table updates as to ensure that all internal daemons have digested the previous update, before the next one arrives.

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands

**apply-config**
*Command Format*

config apply-patch <*patch-filename*> [dry-run] [verbose]

| Command Option                                                | Purpose                                                 |
| -------------------------------------------------------- | ------------------------------------------------------------ |
|<*patch-filename*> | The file of the JsonPatch file to apply which follows [JSON Patch (RFC6902)](https://tools.ietf.org/html/rfc6902) specifications |
|dry-run | Displays the generates commands going to be executed without running them.  |
|verbose | Provide additional details about each step executed as part of the operation. |

*Command Usage*

| Command                                                  | Purpose                                                      |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| config apply-patch *filename*                  | Applies the given JsonPatch file operations following the [JSON Patch (RFC6902)](https://tools.ietf.org/html/rfc6902) specifications. |
| config apply-patch *filename* dry-run               | Displays the generates commands going to be executed without running them. |
| config apply-patch *filename* verbose                  | Applies the given JsonPatch file operations following the [JSON Patch (RFC6902)](https://tools.ietf.org/html/rfc6902) specifications. The CLI output will include additional details about each step executed as part of the operation. |
| config apply-patch *filename* dry-run verbose        | Displays the generates commands going to be executed without running them. The CLI output will include additional details about each step executed as part of the operation.  |


**checkpoint**

*Command Format*

config checkpoint <*checkpoint-name*> [dry-run] [verbose]

| Command Option                                                | Purpose                                                 |
| -------------------------------------------------------- | ------------------------------------------------------------ |
|<*checkpoint-name*> | The name of the checkpoint where ConfigDB JSON config will saved under |
|dry-run | Displays the generates commands going to be executed without running them.  |
|verbose | Provide additional details about each step executed as part of the operation. |

*Command Usage*

| Command                                                  | Purpose                                                      |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| config checkpoint *checkpoint-name*                  | Will save ConfigDB JSON config as a checkpoint with the name *checkpoint-name*. |
| config checkpoint *filename* dry-run               | Displays the generates commands going to be executed without running them. |
| config checkpoint *filename* verbose                  | Will save ConfigDB JSON config as a checkpoint with the name *checkpoint-name*. The CLI output will include additional details about each step executed as part of the operation. |
| config checkpoint *filename* dry-run verbose        | Displays the generates commands going to be executed without running them. The CLI output will include additional details about each step executed as part of the operation.  |

**checkpoint**

*Command Format*

config rollback <*checkpoint-name*> [dry-run] [verbose]

| Command Option                                                | Purpose                                                 |
| -------------------------------------------------------- | ------------------------------------------------------------ |
|<*checkpoint-name*> | The name of the checkpoint where ConfigDB JSON config will saved under |
|dry-run | Displays the generates commands going to be executed without running them.  |
|verbose | Provide additional details about each step executed as part of the operation. |

*Command Usage*

| Command                                                  | Purpose                                                      |
| -------------------------------------------------------- | ------------------------------------------------------------ |
| config rollback *checkpoint-name*                  | Rolls back the ConfigDB JSON config to the config saved under *checkpoint-name* checkpoint. |
| config rollback *filename* dry-run               | Displays the generates commands going to be executed without running them. |
| config rollback *filename* verbose                  | Rolls back the ConfigDB JSON config to the config saved under *checkpoint-name* checkpoint. The CLI output will include additional details about each step executed as part of the operation. |
| config rollback *filename* dry-run verbose        | Displays the generates commands going to be executed without running them. The CLI output will include additional details about each step executed as part of the operation.  |

#### 3.6.2.2 Show Commands

**apply-patch**
*Command Format*

show apply-patch log [exec | verify | status]

| Command                        | Purpose                                                      |
| ------------------------------ | ------------------------------------------------------------ |
| show apply-patch log exec   | Displays a log of all the ConfigDB operations executed including<br/>those that failed. In case of a failed operation, it displays an<br/>error message against the failed operation. |
| show apply-patch log verify | Displays a log all the ConfigDB operations that failed,  <br>along with an error message. It does not display the <br/>operations that were successful. |
| show apply-patch log status | Displays the status of last successful patch application<br/>operation since switch reboot. |

**rollback**
*Command Format*

show rollback log [exec | verify | status]

| Command                        | Purpose                                                      |
| ------------------------------ | ------------------------------------------------------------ |
| show rollback log exec   | Displays a log of all the ConfigDB operations executed including<br/>those that failed. In case of a failed operation, it displays an<br/>error message against the failed operation. |
| show rollback log verify | Displays a log all the ConfigDB operations that failed,  <br>along with an error message. It does not display the <br/>operations that were successful. |
| show rollback log status | Displays the status of last successful config rollback<br/>operation since switch reboot. |


#### 3.6.2.3 Debug Commands

Use the *verbose* option to view additional details while executing the different commands.

# 4 Flow Diagrams

# 5 Error Handling

If an error is encountered during executing any of the commands, the error is reported to the user. The system does not do any recovery actions, and leaves it up to the user to decide.

# 6 Serviceability and Debug
All commands logs are stored in systemd-journal and syslog.


# 7 Warm Boot Support
N/A


# 8 Scalability
N/A

# 9 Unit Tests
| Test Case | Description |
| --------- | ----------- |
|1|Add a new table.|
|2|Remove an existing table.|
|3|Modify values of an existing table entry.|
|4|Modify value of an existing item an array value.|
|5|Add a new item to an array  value.|
|6|Remove an item form an array value.|
|7|Add a new key to an existing table.|
|8|Remove a key from an existing  table.|