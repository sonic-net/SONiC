
# FDB GET support

Implement GET support for FDB entries using CLI/REST/gNMI SONiC management framework interfaces.

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
[Table 2: FDB Test-cases](#table-2-fdb-test-cases)


# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 09/10/2019  |  Venkatesan Mahalingam      | Initial version                   |

# About this Manual
This document provides general information about FDB management GET operation for FDB-table in SONiC.
# Scope
Covers Northbound GET request for the FDB entries, as well as Unit Test cases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| FDB                      | Forwarding Database


# 1 Feature Overview

The documents covers the FDB GET requests on (CLI/REST/gNMI) FDB-Table for fetching the data from the back-end to the user using SONiC managment framework.

## 1.1 Requirements
### 1.1.1 Functional Requirements

Provide management framework GET support to existing SONiC capabilities with respect to FDB.

### 1.1.2 Configuration and Management Requirements
 - Implement FDB CLI show Commands
 - REST GET support for FDB
 - gNMI GET support for FDB

### 1.1.3 Scalability Requirements
N/A
### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach
Provide transformer methods in sonic-management-framework container for displaying MAC entries.
### 1.2.2 Container
All code changes will be done in management-framework container

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
show commands for dumping out the MAC entries present in system via gNMI, REST and CLI.

## 2.2 Functional Description
Provide CLI show commands for displaying MAC entries.

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to add support for fetching and showing MAC entries present in the system.

To support MAC entries GETs, data is fetched from "FDB_TABLE".

For every CLI option, GET all will be done on FDB_TABLE and than as per the options provided by the user, CLI will filter out the response and will display appropriate results.

## 3.2 DB Changes
### 3.2.1 CONFIG DB
N/A

### 3.2.2 APP DB
Will be reading FDB_TABLE for show commands.

### 3.2.3 STATE DB
N/A
### 3.2.4 ASIC DB
N/A
### 3.2.5 COUNTER DB
N/A
## 3.3 Switch State Service Design
N/A
### 3.3.1 Orchestration Agent
N/A
### 3.3.2 Other Process
N/A
## 3.4 SyncD
N/A
## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models
The following OpenConfig YANG model is used to implement GET support for FDB entries.
[openconfig-network-instance-l2.yang](https://github.com/openconfig/public/blob/master/release/models/network-instance/openconfig-network-instance-l2.yang#L292)
```diff
module: openconfig-network-instance
    +--rw network-instances
+      +--rw network-instance* [name]
+         +--rw name                       -> ../config/name
+         +--rw fdb
          |  +--rw config
          |  |  +--rw mac-learning?      boolean
          |  |  +--rw mac-aging-time?    uint16
          |  |  +--rw maximum-entries?   uint16
          |  +--ro state
          |  |  +--ro mac-learning?      boolean
          |  |  +--ro mac-aging-time?    uint16
          |  |  +--ro maximum-entries?   uint16
+         |  +--rw mac-table
+         |     +--rw entries
+         |        +--rw entry* [mac-address vlan]
+         |           +--rw mac-address    -> ../config/mac-address
+         |           +--rw vlan           -> ../config/vlan
          |           +--rw config
          |           |  +--rw mac-address?   yang:mac-address
          |           |  +--rw vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
          |           +--ro state
          |           |  +--ro mac-address?   yang:mac-address
          |           |  +--ro vlan?          -> ../../../../../../vlans/vlan/config/vlan-id
          |           |  +--ro age?           uint64
+         |           |  +--ro entry-type?    enumeration
          |           +--rw interface
          |              +--rw interface-ref
          |                 +--rw config
          |                 |  +--rw interface?      -> /oc-if:interfaces/interface/name
          |                 |  +--rw subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
          |                 +--ro state
+         |                    +--ro interface?      -> /oc-if:interfaces/interface/name
          |                    +--ro subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
```
### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
N/A
#### 3.6.2.2 Show Commands
The following CLI commands dump the output of internal FDB entries from STATE_DB with various options (filters), for example, filter based on MAC address, entry type (static/dynamic), VLAN interface, physical/port-channel interfaces and MAC address table count ..etc.

##### 3.6.2.2.1 show mac address-table
This command dumps all the MAC entries present in the system.
```
sonic# show mac address-table 
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
11          00:00:00:00:00:01   STATIC        Ethernet0           
100         00:00:00:00:00:10   DYNAMIC       Ethernet36          
20          00:00:00:00:00:02   DYNAMIC       Ethernet4           
30          00:00:00:00:00:03   STATIC        Ethernet8           
40          00:00:00:00:00:04   DYNAMIC       Ethernet12          
50          00:00:00:00:00:05   STATIC        Ethernet16          
60          00:00:00:00:00:06   DYNAMIC       Ethernet20          
70          00:00:00:00:00:07   STATIC        Ethernet24          
80          00:00:00:00:00:08   DYNAMIC       Ethernet28          
90          00:00:00:00:00:09   STATIC        Ethernet32          
10          00:00:00:00:00:98   STATIC        Ethernet0           
99          00:00:00:00:00:99   STATIC        PortChannel10       
```

##### 3.6.2.2.2 show mac address-table address <48-bit mac-addres id>
This command provides the MAC entries matching the particular mac-id present in the system.
```
sonic# show mac address-table address 
  nn:nn:nn:nn:nn:nn  48 bit MAC address

sonic# show mac address-table address 00:00:00:00:00:01
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
11          00:00:00:00:00:01   STATIC        Ethernet0           
sonic# 
```

##### 3.6.2.2.3 show mac address-table Vlan <vlan-id>
This command provides the MAC entries matching the particular vlan-id present in the system.
```
sonic# show mac address-table Vlan 10
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
10          00:00:00:00:00:101  STATIC        Ethernet0           
```

##### 3.6.2.2.4 show mac address-table count
This command provides the number of MAC entries present in the system.
```
sonic# show mac address-table count
MAC Entries for all vlans :  13                  
Dynamic Address Count :  5                   
Static Address (User-defined) Count :  8                   
Total MAC Addresses in Use: 13                  
sonic# 
```

##### 3.6.2.2.5 show mac address-table interface Ethernet <port-id>
This command provides the number of MAC entries matching the particular physical port-id present in the system.
```
sonic# show mac address-table interface Ethernet 0
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
11          00:00:00:00:00:01   STATIC        Ethernet0           
10          00:00:00:00:00:98   STATIC        Ethernet0           
sonic# 
```

##### 3.6.2.2.6 show mac address-table interface PortChannel <portchannel-id>
This command provides the number of MAC entries matching the particular physical portchannel-id present in the system.
```
sonic# show mac address-table interface PortChannel 10
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
99          00:00:00:00:00:99   STATIC        PortChannel10       
```

##### 3.6.2.2.7 show mac address-table interface static
This command provides the number of static MAC entries matching present in the system.
```
sonic# show mac address-table static
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
11          00:00:00:00:00:01   STATIC        Ethernet0           
30          00:00:00:00:00:03   STATIC        Ethernet8           
50          00:00:00:00:00:05   STATIC        Ethernet16          
70          00:00:00:00:00:07   STATIC        Ethernet24          
90          00:00:00:00:00:09   STATIC        Ethernet32          
10          00:00:00:00:00:98   STATIC        Ethernet0           
99          00:00:00:00:00:99   STATIC        PortChannel10      
```

##### 3.6.2.2.8 show mac address-table interface dynamic
This command provides the number of dynamic MAC entries matching present in the system.
```
sonic# show mac address-table dynamic
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
100         00:00:00:00:00:010  DYNAMIC       Ethernet36          
20          00:00:00:00:00:02   DYNAMIC       Ethernet4           
40          00:00:00:00:00:04   DYNAMIC       Ethernet12          
60          00:00:00:00:00:06   DYNAMIC       Ethernet20          
80          00:00:00:00:00:08   DYNAMIC       Ethernet28          
```

##### 3.6.2.2.9 show mac address-table interface static address <48 bit mac-address id>
This command provides the number of static MAC entries matching the particular mac-address present in the system.
```
show mac address-table static address 00:00:00:00:00:01
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
10          00:00:00:00:00:01   STATIC        Ethernet0           
11          00:00:00:00:00:01   STATIC        Ethernet0      
```

##### 3.6.2.2.10 show mac address-table interface dynamic address <48 bit mac-address id>
This command provides the number of dynamic MAC entries matching the particular mac-address present in the system.
```
sonic# show mac address-table dynamic address 00:00:00:00:00:06
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
60          00:00:00:00:00:06   DYNAMIC       Ethernet20          
```

##### 3.6.2.2.11 show mac address-table interface static Vlan <id>
This command provides the number of static MAC entries matching the particular vlan-id present in the system.
```
show mac address-table static Vlan 11
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
11          00:00:00:00:00:01   STATIC        Ethernet0      
```

##### 3.6.2.2.12 show mac address-table interface dynamic Vlan <id>
This command provides the number of dynamic MAC entries matching the particular Vlan-id present in the system.
```
sonic# show mac address-table dynamic Vlan 60
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
60          00:00:00:00:00:06   DYNAMIC       Ethernet20          
```

##### 3.6.2.2.13 show mac address-table interface static interface Ethernet <id>
This command provides the number of static MAC entries matching the particular physical interface port-id present in the system.
```
show mac address-table static interface Ethernet 8
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
30          00:00:00:00:00:03   STATIC        Ethernet8          
```

##### 3.6.2.2.14 show mac address-table interface dynamic interface Ethernet <id>
This command provides the number of dynamic MAC entries matching the particular physical interface port-id present in the system.
```
sonic# show mac address-table dynamic interface Ethernet 12
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
40          00:00:00:00:00:04   DYNAMIC       Ethernet12          
```

##### 3.6.2.2.15 show mac address-table interface static interface PortChannel <id>
This command provides the number of static MAC entries matching the particular portchannel-id present in the system.
```
sonic# show mac address-table static interface PortChannel 10
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
99          00:00:00:00:00:99   STATIC        PortChannel10       
```

##### 3.6.2.2.16 show mac address-table interface dynamic interface PortChannel <id>
This command provides the number of dynamic MAC entries matching the particular portchannel-id present in the system.
```
sonic# show mac address-table static interface PortChannel 11
-----------------------------------------------------------
VLAN         MAC-ADDRESS         TYPE         INTERFACE           
-----------------------------------------------------------
98          00:00:00:00:00:95   DYNAMIC       PortChannel11       
```

#### 3.6.2.3 Debug Commands
N/A

### 3.6.3 REST API Support
#### 3.6.3.1 GET
##### Get all support for MAC entries
- 'openconfig-network-instance:network-instances/network-instance={name}/fdb/mac-table/entries'

##### Get MAC entry with MAC address filter
- 'openconfig-network-instance:network-instances/network-instance={name}/fdb/mac-table/entries/entry={mac-address},{vlan}'



# 4 Flow Diagrams
N/A

# 5 Error Handling
N/A

# 6 Serviceability and Debug
N/A

# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
The following test cases will be tested using CLI/REST/GNMI management interfaces.
### Table 2: FDB-Test-Cases
| Test Name | Test Description |
| :------ | :----- |
| show mac address-table | Verify if all of the mac entries present in the system are being displayed. |
| show mac address-table count | Verify number of static or dynamic MAC present and total MAC present in the system |
| show mac address-table Vlan <id> | Verify if only MAC entries matching VLAN-id are displayed. |
| show mac address-table interface Ethernet <port-id> | Verify if only MAC entries matching Ethernet port-id are displayed. |
| show mac address-table interface PortChanel <port-id> | Verify if only MAC entries matching PortCahnell-id are displayed. |
| show mac address-table interface address <mac-address-id> | Verify if only MAC entries matching mac-address are displayed. |
| show mac address-table interface static | Verify if only static MAC entries are displayed. |
| show mac address-table interface dynamic | Verify if only dynamic MAC entries are displayed. |
| show mac address-table interface static address <mac-id> | Verify if only static MAC entries matching mac-id are displayed. |
| show mac address-table interface dynamic address <mac-id> | Verify if only dynamic MAC entries matching mac-id are displayed. |
| show mac address-table interface static Vlan <id> | Verify if only static MAC entries matching Vlan id are displayed. |
| show mac address-table interface dynamic Vlan <id> | Verify if only dynamic MAC entries matching Vlan id are displayed. |
| show mac address-table interface static interface Ethernet <id> | Verify if only static MAC entries matching Ethernet port-id are displayed. |
| show mac address-table interface dynamic interface Ethernet <id> | Verify if only dynamic MAC entries matching Ethernet port-id are displayed. |
| show mac address-table interface static interface PortChannel <id> | Verify if only static MAC entries matching PortChannel-id are displayed. |
| show mac address-table interface dynamic interface PortChannel <id> | Verify if only dynamic MAC entries matching PortChannel-id are displayed. |


#### Configuration(PATCH) and GET via gNMI/REST
- Verify the JSON response for GET requests
 
