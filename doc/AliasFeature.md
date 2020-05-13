# Alias Feature

Implement alternative naming convention (alias) for ethernet interfaces via  CLI/REST/gNMI  in SONiC management framework.

# High Level Design Document

#### Rev 0.1

# Table of Contents

- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [About This Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)

# List of Tables

[Table 1: Abbreviations](#table-1-abbreviations)

# Revision

| Rev  | Date       | Author       | Change Description |
| ---- | ---------- | ------------ | ------------------ |
| 0.1  | 05/01/2020 | Justine Jose | Initial draft      |
|      |            |              |                    |
|      |            |              |                    |

# About this Manual

This document provides general information about alias related syntax & overview for ethernet Interfaces in break out & non-breakout mode.

# Scope

Covers general design for supporting alias feature.

# Definition/Abbreviation

### Table 1: Abbreviations

# 1 Feature Overview

The document covers the various interfaces for alias feature using SONiC management framework. Currently in SONiC, the ethernet interfaces are shown as a flat number. This flat interface numbering does not give mapping about actual ports that are mapped to the interface number. By enabling alias feature, user has better usability & mapping for actual port numbers.

## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide ability to have an alternative configuration for Ethernet Interface using SONiC management framework.

### 1.1.2 Configuration and Management Requirements

- Two modes to represent interfaces "native mode" & "alias mode".
- Implement alias related config & show commands.
- REST & gNMI set/get support for alias mode.

### 1.1.3 Scalability Requirements

### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach

- By default system will boot in native mode. Native mode is where interfaces are displayed as Ethernet 1, Ethernet 4, Ethernet 8 etc. This also ensures that backwards compatibility is maintained.
- Once alias is enabled, all subsequent CLI, REST & gNMI interfaces will use the alternative name for ethernet interface configuration & retrieval.
- Existing SSH sessions : TBD.  

### 1.2.2 Container

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases

## 2.2 Functional Description

# 3 Design

## 3.1 Overview

- When alias mode is enabled, ethernet interfaces will be represented as Eth[slot/port/breakout-port], where slot will start from 1 and port/breakout-port numbers will start from 1. This name format is fixed and will not have references to interface speed. For e.g Eth1/1 (in non breakout mode), Eth1/1/1 (in breakout mode).
- The alias name {e.g Eth1/1) is picked from platform.json file. All platforms to be updated with this format for port name.
- For dynamically using the right string for ethernet interfaces (i.e Ethernet 4 in native mode & eth 1/4 in alias mode), XML file has to be modified to use the correct PTYPE. `PHY_INTERFACE` has to be used as PTYPE for Ethernet Interface.   
Example:
```
<PARAM
    name="phy-if-name"
    help="Select an interface"
    ptype="PHY_INTERFACE"
/>
```

- Annotations to be added for alias

  What App-owners need to do?  

  *1. Add “value-transformer” annotation for the leaves & keys that need special handling, in the sonic-yang annot file.*  
  *2. Write value-transformer callback api*  

  Actions that Xfmr-infra will do:  
  *1. Process dbDataMap & invoke value-transformer, if present.*


  **Use case:**

“value-transformer” (callback_xfmr) annotated for a leaf(leaf-A) in a sonic-yang(assume soinc-A.yang), will be invoked for that leaf(leaf-A).

If leaf-A in sonic-A.yang is referred from multiple other yang-leaves(assume leaf-B in sonic-B.yang & leaf-C in sonic-C.yang has leaf-ref to leaf-A in sonic-A.yang), then the “callback_xfmr” will be inherited & invoked for these leaves(leaf-B & C) as well, without any explicit annotation(i.e. no “value-transformer” annotation is needed for leaf-B or leaf-C).

  User can override inherited value-transformer, by annotating a new value-xfmr at that level. i.e. If an explicit value-transformer(“callback_NEW_xfmr”) is annotated for leaf-B in soinc-B.yang(which has leaf-ref to leaf-A), then “callback_NEW_xfmr” will be invoked for leaf-B.



  E.g. For “aliasing” feature, “/sonic-port/PORT/PORT_LIST/ifname” is annotated with value-transformer ("**alias_value_xfmr**"). This api("**alias_value_xfmr**") will be invoked for `/sonic-port/PORT/PORT_LIST/ifname`, as well as for all the yang-leaves, which has leaf-ref to this (like `/sonic-acl/ACL_TABLE/ACL_TABLE_LIST/ports`, `/sonic-udld/UDLD_PORT/UDLD_PORT_LIST/ifname`, `/sonic-mirror-session/MIRROR_SESSION/MIRROR_SESSION_LIST/dst_port` etc.).

  **Sample yang annotation**:

[sonic-port-annot.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/annotations/sonic-port-annot.yang)
  ```
  deviation /prt:sonic-port/prt:PORT/prt:PORT_LIST/prt:ifname {
       deviate add {
           sonic-ext:value-transformer "alias_value_xfmr";
       }
   }
  ```

  **API signature:**

  ​       `func alias_value_xfmr(inParams XfmrDbParams) (string, error)`



  **XfmrDbParams contents**
```
  type XfmrDbParams struct {
    db             db.DBNum
    oper           int
    tableName      string
    key            string
    field          string
    fieldYangType  yang.TypeKind
    value          string  
  }
```

  **Below is the data flow**

  **CRU operation (OC & Sonic) **:

| **Existing  implementation**                                 | **New  implementation**                                      |
| ------------------------------------------------------------ | :----------------------------------------------------------- |
| For any CRU request that reaches Xfmr, xfmr-infra will process payload & invoke overloaded  functions (i.e fieldxfmr, subtreexfmr…), if present.  It then creates dbDataMap and performs DB operations on dbDataMap | For any CRU that reaches Xfmr, Xfmr-infra will process payload  & invoke any overloaded  functions if present (i.e fieldxfmr, subtreexfmr…). It then creates dbDataMap & invokes value-transformer( when present), process dbDataMap and  create a new processed-dbDataMap· DB operations are now performed on processed-dbDataMap. |



   ***GET operation(OC & Sonic)**

| **Existing  implementation**                                 | **New implementation**                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| For any CRU request that reaches Xfmr, Xfmr-infra will read data from db and  create dbDataMap.  It then invokes overloaded  functions(fieldxfmr, subtreexfmr…) with dbDataMap. Fills the ygot tree with  data from dbDataMap & merges it with ygot-tree from subtree-xfmr and sends response back. | For any CRU request that reaches Xfmr, xfmr-infra will read data from db and create dbDataMap. First value-xfmr (if present) is invoked, dbDataMap is processed and a new processed-dbDataMap  is created.  Overloaded  functions(fieldxfmr, subtreexfmr…) with processed-dbDataMap will be invoked next. Fills the ygot tree with  data from dbDataMap & merges it with ygot-tree from subtree-xfmr and sends response back. |

   **Sub-tree Transformer**: In cases where applications use subtree transformer, then need to use an API that will return the alias string. The API will internally figure out if alias is enabled or not.

   Following are the APIs used:  
   These APIs are available in `translib/utils` package.

   **GetNativeNameFromUIName**  
   `func GetNativeNameFromUIName(ifName *string) *string`  

   Retrieves native interface name from user input name, if the alias mode is enabled. User input name can be alias or native interface. API will provide native interface name if the user input is alias name, otherwise it will return the native interface name passed to the API. If the alias mode is not enabled, API will return the input string passed.

   **GetAliasNameFromUIName**  
   `func GetAliasNameFromUIName(ifName *string) *string`  

   Retrieves alias interface name from user input name, if the alias mode is enabled. User input name can be alias or native interface. API will provide alias name if the user input is native interface name, otherwise it will return the alias name passed to the API. If the alias mode is not enabled, API will return the input string passed.

## 3.2 DB Changes

### 3.2.1 CONFIG DB

#### 3.2.1.1

### 3.2.2 APP DB

### 3.2.3 STATE DB

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design

### 3.3.1 Orchestration Agent

### 3.3.2 Other Process

## 3.4 SyncD

## 3.5 SAI

## 3.6 User Interface

### 3.6.1 Data Models
Yang model used for alias mode handling  
[sonic-device-metadata.yang](https://github.com/project-arlo/sonic-mgmt-framework/blob/master/models/yang/sonic/sonic-device-metadata.yang)  

Supported yang objects and attributes are highlighted in green:
```diff
module: sonic-device-metadata
    +--rw sonic-device-metadata
       +--rw DEVICE_METADATA
          +--rw DEVICE_METADATA_LIST* [name]
             +--rw name                          string
+            +--rw aliasMode                     boolean
```

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands

#### Alias mode configuration

`[no] alias enable`
```
sonic(config)# alias enable
sonic(config)# no alias enable
```
#### Config commands when alias mode is enabled
`Eth 1/2`, `Eth1/2`, and `e1/2` options are supported to get into alias interface config mode.  The parser converts all to `Eth1/2`.

```
sonic(config)# interface e1/2
sonic(conf-if-Eth1/2)#
```
```
sonic(conf-if-Eth1/2)# ip address 2.2.2.2/24
```

#### 3.6.2.2 Show Commands

#### Display alias mode  

`show alias`
```
sonic(config)# alias enable
sonic# show alias
Alias mode is enabled
```
```
sonic(config)# no alias enable
sonic# show alias
Alias mode is disabled
```
#### Show commands when alias mode is enabled
```
show vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
2          Inactive    A  Eth1/3
                       T  Eth1/5/2
                       T  Eth1/10
```




#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

The following table maps SONiC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  \u2013 meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  \u2013 meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONiC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONiC.

| CLI Command | Compliance | IS-CLI Command (if applicable) | Link to the web site identifying the IS-CLI command (if applicable) |
| ----------- | ---------- | ------------------------------ | ------------------------------------------------------------ |
|             |            |                                |                                                              |

### 3.6.3 REST API Support

#### 3.6.3.1

##### Following REST operations will be supported

**PATCH, PUT, DELETE and GET**

- `​/sonic-device-metadata:sonic-device-metadata​/DEVICE_METADATA​/DEVICE_METADATA_LIST={name}​/aliasMode`


# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test and Automation

The following test cases will be tested using CLI/REST/gNMI management interfaces.
#### Configuration and Show via CLI

| Test Name | Test Description |
| :------ | :----- |
| Default alias mode verification | Verify alias mode is disabled by default |
| Configure alias mode | Verify whether alias mode is enabled using show command |
| Alias mode verification | Alias mode can be verified using config and show commands involving physical inetrface whether alias name has taken effect |
| Disable alias mode  | Verify whether alias mode is disabled using show command |
| Native mode verification | Alias mode can be verified using config and show commands involving physical inetrface whether native name has taken effect |
| Save and reload test | Save the config and reload the box, make sure that the system comes up with alias enabled mode |


#### Configuration via gNMI

Same as CLI configuration test, but using gNMI SET request

#### Get configuration via gNMI

Same as CLI show test, but using gNMI GET request, verify the JSON response.

#### Configuration via REST

Same as CLI configuration test, but using REST request

#### Get configuration via REST

Same as CLI configuration test, but using REST request

#### Automation

Spytest cases will be implemented for new CLI and APIs.
