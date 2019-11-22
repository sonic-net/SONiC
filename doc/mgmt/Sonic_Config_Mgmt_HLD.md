# Feature Name
Implement management support using CLI/REST/gNOI interfaces for Configuration Management Operations.

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
| 0.1 | 10/30/2019  |  Bhavesh Nisar     | Initial version                   |

# About this Manual
This document provides information on the management interfaces for Configuration Management Operations.
# Scope
The scope of this document is limited to the northbound interfaces supported by the new management framework, i.e., CLI, gNOI and REST. The functional behavior of these operations is not modified and can be referred in the SONiC Documents.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| NBI                      | North Bound Interface               |

# 1 Feature Overview

The feature addresses the equivalent of the existing cLick CLI commands.  The  implementation is contained within the Management Framework container.
Their is no openconfig data yang defined for this feature. A new SONiC yang will be introduced for the NBI.

## 1.1 Requirements

### 1.1.1 Functional Requirements
Not Applicable

### 1.1.2 Configuration and Management Requirements

Operations:
1. Save running configuration to default. <br>
   CLI Command : write memory <br>
   EXEC Level <br>
   Write to file /etc/sonic/config_db.json  <br>

2. Copy configuration from file to running and reload. <br>
   CLI Command : copy file://<*filename*> running-configuration [overwrite] <br>
   EXEC Level <br>
   Parameter: <*filename*>: user input : file://etc/sonic/<*filename*\>  <br> &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp; config can only be loaded from /etc/sonic/ directory <br>
   Parameter: overwrite (optional) - flush configDB and restart core services. <br>

3. Save running configuration to file.  <br>
   CLI Command: copy running-configuration file://<*filename*\>  <br>
   EXEC Level  <br>
   Parameter: <*filename*> -  user input: file://etc/sonic/<*filename*> <br> &ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;&ensp;   config can only be saved in /etc/sonic/ directory

4. Copy startup configuration to running-configuration and reload. <br>
CLI Command: copy startup-configuration running-configuration  [overwrite]<br>
EXEC Level  <br>
Parameter: overwrite (optional) - flush configDB and restart core services.

The click CLI additionally supports 'config load_mgmt' and 'config load_minigraph' commands. These operations are SONiC specific. The new sonic management framework will handle the management interface related configuration through the NBI interface. The current json format of configDB replaces the xml format of minigraph.

### 1.1.3 Scalability Requirements
Not Applicable

### 1.1.4 Warm Boot Requirements
Not Applicable

## 1.2 Design Overview
### 1.2.1 Basic Approach
The operations are invoked via RPC construct of the yang interface. The sonic management framework callback is defined in the sonic-annotation.yang file. The operations are executed on the host service via the dBus framework. The dbus hostservice will execute the operations by calling the config click cli script.

### 1.2.2 Container
This feature is contained within the sonic-mgmt-framework container.

### 1.2.3 SAI Overview
Not Applicable.

# 2 Functionality
## 2.1 Target Deployment Use Cases
Not Applicable

## 2.2 Functional Description
Not Applicable

# 3 Design
## 3.1 Overview
Not Applicable

## 3.2 DB Changes
Describe changes to existing DBs or any new DB being added.
### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
Not Applicable

## 3.4 SyncD
Not Applicable

## 3.5 SAI
Not Applicable

## 3.6 User Interface
### 3.6.1 Data Models

A new sonic yang (sonic-config-mgmt.yang) provides the interface for configuration and status.

```
typedef filename-uri-type {
  description
    "Support for following URI format:
       file://etc/sonic/filename
       Exception: running-configuration (running configDB)
                  startup-configuration (default startup config file i.e. file://etc/sonic/config_db.json)";
  type string {
    pattern "((file):.*)";
    pattern "running-configuration";
    pattern "startup-configuration";
  }
}
module: sonic-config-mgmt

  rpcs:
    +---x copy
       +---w input
       |  +---w source?        string
       |  +---w overwrite?     boolean
       |  +---w destination?   string
       +--ro output
          +--ro status?   string

```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
As described in section 1.1.2

#### 3.6.2.2 Show Commands
Not Applicable

#### 3.6.2.3 Debug Commands
Not Applicable

#### 3.6.2.4 IS-CLI Compliance
The following table maps SONIC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  – meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  – meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONIC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONIC.

|       CLI Command       | Compliance   | click CLI                    | Deviation
|:-----------------------:|:-------------|------------------------------|---------------
| write memory            | IS-CLI-like  |  config save                  |
|  copy <*filename*> running-configuration [overwrite]    |    IS-CLI-like          |  config load <*filename*><br> config reload <*filename*>              | The overwrite option flushes DB and restarts core services.
| copy running-configuration <*filename*\>  |     IS-CLI-like         |  config save <*filename*>                 |
|copy startup-configuration  running-configuration [overwrite] | IS-CLI-like   | config  load <br> config reload | The overwrite option flushes DB and restarts core services.  |   |   |

**Deviations from IS-CLI:** If there is a deviation from IS-CLI, Please state the reason(s).


### 3.6.3 REST API Support
Rest API is supported through the sonic-config-mgmt.yang.

# 4 Flow Diagrams
Not applicable.

# 5 Error Handling
Not applicable.

# 6 Serviceability and Debug
Not applicable.

# 7 Warm Boot Support
Not applicable.

# 8 Scalability
Not applicable.

# 9 Unit Test
List unit test cases added for this feature including warm boot.
CLI test cases
1. Execute 'write memory'. Default path applied. Verify config_db.json file.
2. Execute 'copy \<filename\> running-configuration [overwrite]'. Verify config flush. New config loaded from *filename* into redis:configDB with restart of core services.
3. Execute 'copy startup-configuration running-configuration [overwrite]'. Verify config flush. New config loaded from default:/etc/sonic/config_db.json into redis:configDB with restart of core services.
4. Execute 'copy \<filename\> running-configuration . Verify config from *filename* loaded in redis:configDB.
5. Execute 'copy startup-configuration running-configuration . Verify config loaded from default:/etc/config/config_db.json into redis:configDB.
6. Execute 'copy running-configuration <*filename*>. Verify configdb saved into given file.
