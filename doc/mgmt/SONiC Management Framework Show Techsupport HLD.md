# Show techsupport
Diagnostic information aggregated presentation
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)

# List of Tables

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 10/06/2019  |   Kerry Meyer      | Initial version                   |

# About this Manual
This document provides general information about presentation of aggregated diagnostic information for the SONiC subsystem via the Management Framework infrastructure.
# Scope
This document describes the high level design for the "show techsupport" command implementation under the control of the Management Framework infrastructure. It is intended to cover the general approach and method for providing a flexible collection of diagnostic information items and a mechanism for adding new items to the list of information to be provided. It also considers the basic mechanisms to be used for the various types of information to be aggregated. It does not address specific details for collection of all supported classes of information.

# Definition/Abbreviation

# 1 Feature Overview

Provide Management Framework functionality to process the "show techsupport" command:
    - Create an aggregated file containing the information items needed for analysis and diagnosis of problems occurring during switch operations.
    - Support reduction of aggregated log file information via an optional "--since" parameter specifying the desired logging start time.

## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide a Management Framework based implementation of the "show techsupport" command. Match the functionality currently provided for this command via a Click-based host interface.

### 1.1.2 Configuration and Management Requirements
- IS-CLI style implementation of  the "show techsupport" command
- REST API support
- gNMI Support

(See Section 3 for additional details.)

### 1.1.3 Scalability Requirements

Time and storage space constraints: The large number of information items collected and the potentially large size of some of the items (e.g. interface information display in a large system) present an exposure to the risk of long processing times and high demands on disk storage space. The current implementation (within the Click infrastructure mechanism) provides reasonable performance, executing within ~60 seconds on a typically scaled switch. It stores the information for a single dump of a typically scaled switch in a compressed "tar" file occupying ~2MB of storage space. The Management Framework implementation should strive to achieve similar performance and data storage targets.
### 1.1.4 Warm Boot Requirements
N/A
## 1.2 Design Overview
### 1.2.1 Basic Approach
This feature will be implemented using the Management Framework infrastructure supplemented with customized access mechanisms for handling "non-DB" data items.

### 1.2.2 Container
The user interface (front end) portion of this feature is implemented within the Management Framework container.

### 1.2.3 SAI Overview
N/A (non-hardware feature)

# 2 Functionality
## 2.1 Target Deployment Use Cases
This feature provides a quick and simple mechanism for network administrators or other personnel with no detailed knowledge of switch internal details to gather an extensive set of information items by using a single command. These items provide critical information to help development and sustaining engineering teams in the analysis and debugging of problems encountered in deployment and test environments.
## 2.2 Functional Description
The set of items to be gathered for a given software release is defined by the development team. It is specified in a way that enables run-time access to the desired set of information items to be collected. The definition of the set of information items to be collected includes specification of the access function to be used for each item in the list to gather the information, format it as needed, and pack it into the output file. The location of the resulting output file is provided to the requesting client at the completion of command execution.

# 3 Design
## 3.1 Overview
The "show techsupport" command causes invocation of an RPC sent from the management framework to a process in the host to cause collection of a list of flexibly defined sets of diagnostic information (information "items"). The collected list of items is stored in a compressed "tar" file with a unique name. The command output provides the location of the resulting compressed tar file.

The "since" option can be used, if desired, to restrict the time scope for some of the information items (e.g. logs) to be collected. This options are passed to the host process for use during invocation of the applicable information gathering sub-functions.

Help information and syntax details are provided if the command is executed with the "-h", "--help" or "-?" option.

## 3.2 DB Changes
N/A
### 3.2.1 CONFIG DB
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
N/A
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
The "show techsupport" feature requires RPC support in a process running within the host context. The host process handling the RPC is responsible for dispatching "show techsupport" requests from the management framework container to trigger allocation of an output file, gathering and packing of the required information into the output file, and sending a response to the management framework RPC agent to specify the name and path of the output file.

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models
The following Sonic Yang model is used for implementation of this feature:

module: sonic-show-techsupport

  rpcs:
    +---x sonic-show-techsupport-info
       +---w input
       |  +---w date?   yang:date-and-time
       +--ro output
          +--ro output-filename?   string


### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
N/A
#### 3.6.2.2 Show Commands

show techsupport [since <DateTime>] — Gather information for troubleshooting. Display the name of a file containing the resulting group of collected information items in a compressed "tar" file.

Syntax Description:

|    Keyword    | Description |
|:-----------------|:-----------|
| since DateTime | This option uses a text string (in the format returned by the Linux "date" command) to restrict the time scope for some of the information items to be collected (e.g. log files). It is passed to the host process and, if the date/time specification is valid, it is used during invocation of the applicable information gathering sub-functions.

Command Mode: User EXEC

Example:

sonic# show techsupport

/var/dump/sonic_dump_sonic_20191008_082312.tar.gz

--------------------


#### 3.6.2.3 Debug Commands
N/A
#### 3.6.2.4 IS-CLI Compliance
N/A (TBD)

The following table maps SONIC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  – meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  – meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONIC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONIC.

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---:|:-----------:|:------------------:|-----------------------------------|
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |

**Deviations from IS-CLI:** If there is a deviation from IS-CLI, Please state the reason(s).

### 3.6.3 REST API Support
TBD: (The base for RPC based Sonic Yang models is currently being developed.)

# 4 Flow Diagrams

# 5 Error Handling
N/A

# 6 Serviceability and Debug
Logging, counters, stats, trace considerations. Please make sure you have incorporated the debugging framework feature. e.g., ensure your code registers with the debugging framework and add your dump routines for any debug info you want to be collected.

# 7 Warm Boot Support
N/A

# 8 Scalability
Refer to section 1.1.3

# 9 Unit Test
- Basic command execution:
  - Trigger: Execute the "show techsupport" command with no parameters.
  - Result: Confirm that the command is accepted without errors and a "result" file name is returned. Confirm that the result file contains the expected set of items. (Examine/expand the contents of the file to ensure that the top level directory tree is correct and that the number of sub-files within the tar file is correct.)

- "since" option (postive test case)
  - Trigger: Execute the command with the "--since" TEXT option with a valid date string specifying a time near the end of one of the  unfiltered output from the first test.
  - Result: Same as the "Basic command execution" case. Additionally, confirm that the expected time filtering has occurred by examining one of the affected sub-files.

- "since" option (negative test case)
    - Trigger1: Execute the command with the "--since" TEXT option with an invalid date string.
    - Trigger2: Execute the command with the "--since" option with no date string.
    - Result: Verify that an error is returned.


# 10 Internal Design Information
N/A
