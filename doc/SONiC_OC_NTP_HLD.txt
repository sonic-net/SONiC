# Feature Name
NTP Support in Management Framework

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
| 0.1 | 05/03 |   Bing Sun         | Initial version                   |
  
  
# About this Manual

This document introduces the support of NTP configuration using management framework. It also describes the mechanism of ntp service upon various NTP configuration changes.

# Scope

This document covers NTP "configuration" and "show" commands based on the OpenConfig YANG model, as well as the backend mechanism required to support each command.
NTP unit tests are also included.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          NTP             |  Network Time Protocol              |
|          ntpd            |  NTP Daemon                         |


# 1 Feature Overview

NTP stands for Network Time Protocol. It is used to synchronize the time of a computer or server to another server or refernce time source.   

SONiC click CLI provides commands to add/delete the IP address of a remote NTP server. Multiple NTP servers can be configured, and both IPv4 an IPv6 are supported. SONiC click CLI also provides the show command to display status of NTP peers.    

With this feature, users will be provided the same capabilities via Management CLI, REST and gNMI using OpenConfig Yang models.
It also provides users to configure NTP source and NTP vrf (Management VRF for now?) for addtional ntp control.

## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities

#### 1.1.1.1 add/delete NTP server      
This installs NTP server information in the Redis ConfigDB and in the ntp.conf file (NTP configuration file).   
The NTP server can be IPv4 address, IPv6 address , or the name of a NTP server.   
Mutliple NTP servers can be configured.
  
#### 1.1.1.2 add NTP source
This installs the global NTP source information in the Redis ConfigDB and in the ntp.conf file. It enables ntpd to listen to the specific source.      
NTP source can be configured as either IP address or interface name.    
Only one NTP source will be installed as the global NTP source. A new configured NTP source will override the existing NTP source.   
  
#### 1.1.1.3 delete NTP source
This deletes the global NTP source entry from the Redis ConfigDB and from the ntp.conf file.   

#### 1.1.1.4 add/delete VRF name
This installs the global NTP VRF information in the Redis ConfigDB. It is used by the ntp configuration script to start the ntpd in a specific VRF context.   
For this release, only Management VRF and default instance are supported(?). When the global NTP VRF is deleted, ntpd will be restarted in the default instance.

#### 1.1.1.5 Get NTP association
This displays the output of "ntpq -p" command.   

### 1.1.2 Backend mechanisms to support configuration and get

#### 1.1.2.1 add/delete NTP server
The creates or deletes a NTP server entry in the Redis ConfigDB.

```
  "NTP_SERVER|10.11.0.1": {
    "type": "hash",
    "value": {
      "NULL": "NULL"
    }
  },
  "NTP_SERVER|2001:aa:aa::a": {
    "type": "hash",
    "value": {
      "NULL": "NULL"
    }
  },
  "NTP_SERVER|pool.ntp.org": {
    "type": "hash",
    "value": {
      "NULL": "NULL"
    }
  }
```

A change in the NTP_SERVER entry triggers hostcfgd to start the NTP configuration script, which in turn writes each NTP server to the ntp.conf and then restart the ntp service.   
   
SONiC click CLI only supports IP address for NTP server. It can be extended to server name as well.   


#### 1.1.2.2 add/delete NTP source

This creates or deletes a global NTP source entry in the Redis ConfigDB. The NTP source can be a L3 interface name or an interface IP address (IPv4 or IPv6).   

```
  "NTP|global": {
    "type": "hash",
    "value": {
      "source": "Ethernet36"
    }
  }
```

A change in this entry triggers hostcfgd to start the NTP configuration script, which in turn writes the ntp source to the ntp.conf and then restart the ntp service.   
Only one global NTP source entry is allowd, and it can be either an interface name or interface IP address.   
   
SONiC click CLI can be extende to include this configuration.


#### 1.1.2.3 add/delete NTP VRF

This creates or deletes a global NTP vrf entry in the Redis ConfigDB. For this release, it can only be "mgmt"(??).

```
  "NTP|global": {
    "type": "hash",
    "value": {
      "vrf": "mgmt"
    }
  }
```

A change in this DB entry triggers hostcfgd to restart ntp service.  
    
When Management VRF is configured, existing SONiC code always restart ntpd in the mgmt vrf context. Since this release introduces support of NTP source, 
NTP may listen to a L3 interface in the default instance even with the presence of Management VRF. As a result, ntp service script needs to be modified 
to restart the NTP service in the configured NTP vrf instance, or restart the ntp service in default instance if this entry is absent.   
   
If data vrf as NTP vrf is also supported, then hostcfgd needs to install localhost in the specified vrf in addition.

SONiC click CLI can be extende to include this configuration.   


#### 1.1.2.4 get NTP associations

Transformer function issues "ntpq -p" command, parses the response and maps the outputs to the OpenConfig NTP states.

### 1.1.3 Functional Requirements

Provide management framework support to    
- configure NTP server   
- configure NTP source   
- configure NTP vrf  

### 1.1.4 Configuration and Management Requirements
- CLI style configuration and show commands   
- REST API support   
- gNMI Support   

Details described in Section 3.

### 1.1.5 Configurations not supported by this feature using management framework:
- NTP authenticate   
- NTP authentication-key   
- configure local server as a NTP server   
- trusted key   
- broadcast mode   

### 1.1.6 Scalability Requirements

### 1.1.7 Warm Boot Requirements

## 1.2 Design Overview

### 1.2.1 Basic Approach
Implement NTP support using transformer in sonic-mgmt-framework.

### 1.2.2 Container
The front end code change will be done in management-framework container including:   
- XML file for the CLI   
- Python script to handle CLI request (actioner)   
- Jinja template to render CLI output (renderer)   
- OpenConfig YANG model for NTP openconfig-system.yang and openconfig-system-ext.yang   
- SONiC NTP model for NTP based on Redis DB schema of NTP   
- transformer functions to    
   * convert OpenConfig YANG model to SONiC YANG model for NTP related configurations   
   * convert from Linux command "ntpq -p" output to OpenConfig NTP state YANG model   

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases
Manage/configure Management VRF via gNMI, REST and CLI interfaces

## 2.2 Functional Description
Provide CLI, gNMI and REST supports for Management VRF handling

## 2.3 Backend change to support new configurations
Provide change in hostcfgd, ntp config script, ntp service script.
SONiC click CLI enhancement if possible.

# 3 Design

## 3.1 Overview

Enhancing the management framework backend code and transformer methods to add support for NTP.

## 3.2 DB Changes

### 3.2.1 CONFIG DB
This feature will allow the user to make NTP configuration changes to CONFIG DB, and get NTP peer states.

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

YANG models needed for NTP handling in the management framework:
1. **openconfig-system.yang**  

2. **openconfig-system-ext.yang**
 
3. **sonic-system-ntp.yang**

Supported yang objects and attributes:
```diff

module: openconfig-system 
      +--rw system

+     +--rw ntp
+     |  +--rw config
      |  |  +--rw enabled?                           boolean
+     |  |  +--rw ntp-source-address?                oc-inet:ip-address
      |  |  +--rw enable-ntp-auth?                   boolean
+     |  |  +--rw oc-sys-ext:ntp-source-interface
+     |  |  |  +--rw oc-sys-ext:interface?      -> /oc-if:interfaces/interface/name
+     |  |  |  +--rw oc-sys-ext:subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
+     |  |  +--rw oc-sys-ext:vrf?                    string
      |  +--ro state
      |  |  +--ro enabled?                           boolean
+     |  |  +--ro ntp-source-address?                oc-inet:ip-address
      |  |  +--ro enable-ntp-auth?                   boolean
      |  |  +--ro auth-mismatch?                     oc-yang:counter64
+     |  |  +--ro oc-sys-ext:ntp-source-interface
+     |  |  |  +--ro oc-sys-ext:interface?      -> /oc-if:interfaces/interface/name
+     |  |  |  +--ro oc-sys-ext:subinterface?   -> /oc-if:interfaces/interface[oc-if:name=current()/../interface]/subinterfaces/subinterface/index
+     |  |  +--ro oc-sys-ext:vrf?                    string
      |  +--rw ntp-keys
      |  |  +--rw ntp-key* [key-id]
      |  |     +--rw key-id    -> ../config/key-id
      |  |     +--rw config
      |  |     |  +--rw key-id?      uint16
      |  |     |  +--rw key-type?    identityref
      |  |     |  +--rw key-value?   string
      |  |     +--ro state
      |  |        +--ro key-id?      uint16
      |  |        +--ro key-type?    identityref
      |  |        +--ro key-value?   string
+     |  +--rw servers
+     |     +--rw server* [address]
+     |        +--rw address    -> ../config/address
+     |        +--rw config
+     |        |  +--rw address?            oc-inet:host
      |        |  +--rw port?               oc-inet:port-number
      |        |  +--rw version?            uint8
      |        |  +--rw association-type?   enumeration
      |        |  +--rw iburst?             boolean
      |        |  +--rw prefer?             boolean
+     |        +--ro state
+     |           +--ro address?              oc-inet:host
      |           +--ro port?                 oc-inet:port-number
      |           +--ro version?              uint8
      |           +--ro association-type?     enumeration
      |           +--ro iburst?               boolean
      |           +--ro prefer?               boolean
+     |           +--ro stratum?              uint8
+     |           +--ro root-delay?           uint32
+     |           +--ro root-dispersion?      uint64
+     |           +--ro offset?               uint64
+     |           +--ro poll-interval?        uint32
+     |           +--ro oc-sys-ext:selMode?   string
+     |           +--ro oc-sys-ext:refid?     inet:host
+     |           +--ro oc-sys-ext:type?      string
+     |           +--ro oc-sys-ext:now?       uint32
+     |           +--ro oc-sys-ext:reach?     uint8


module: sonic-system-ntp

+    +--rw sonic-system-ntp
+       +--rw NTP
+       |  +--rw NTP_LIST* [global_key]
+       |     +--rw global_key    enumeration
+       |     +--rw source?       union
+       |     +--rw vrf?          string
+       +--rw NTP_SERVER
+          +--rw NTP_SERVER_LIST* [server_address]
+             +--rw server_address    inet:host

```

### 3.6.2 CLI


#### 3.6.2.1 Configuration Commands
All commands are executed in `configuration-view`:
```
sonic# configure terminal
sonic(config)#
```

##### 3.6.2.1.1 Configure NTP server
```
sonic(config)#ntp
    server              Configure NTP server
sonic(config)#ntp server 
String  NTP server address or name

sonic(config)# ntp server 10.11.0.1

sonic(config)# ntp server 2001:aa:aa::a

sonic(config)# ntp server pool.ntp.org

```

##### 3.6.2.1.2 Delete NTP server

```
sonic(config)# no ntp server
  String  NTP server address or name

sonic(config)# no ntp server 10.11.0.1

sonic(config)# no ntp server 2001:aa:aa::a

sonic(config)# no ntp server pool.ntp.org

```

##### 3.6.2.1.3 Configure NTP source ip

```
sonic(config)# ntp
    source              Configure source IP address

sonic(config)# ntp source 11.22.33.55

sonic(config)# ntp source 2001:aa:aa::b

```

##### 3.6.2.1.4 Delete NTP source

```
sonic(config)# no ntp source

```

##### 3.6.2.1.5 Configure NTP vrf

```
sonic(config)#
    vrf          Enabling NTP on a VRF

sonic(config)#ntp vrf
  management                  Enable NTP on management VRF
  String(Max: 32 characters)  Enable NTP on non-default VRF

sonic(config)# ntp vrf management

```

##### 3.6.2.1.6 Delete NTP vrf

```
sonic(config)# no ntp
    vrf  Disable NTP on a VRF

sonic(config)# no ntp vrf
  management                  Disable NTP on management VRF
  String(Max: 32 characters)  Disable NTP on non-default VRF

sonic(config)# no ntp vrf management

```

#### 3.6.2.2 Show ntp associations

```
sonic(config)# do show ntp
  associations  NTP associations


sonic(config)# do show ntp associations
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*10.11.0.1       10.11.8.1        4 u   28   64    1    0.183    1.499   2.625
+2001:aa:aa::b   60.39.129.68    10 u   27   64    1    0.638  2171.31   0.411
+10.11.0.2       10.11.8.1        4 u   24   64    1    0.240  -13.957  12.786
* master (synced), # master (unsynced), + selected, - candidate, ~ configured

```

#### 3.6.2.3 Debug Commands

#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing NTP configuration information from CONFIG DB.
      Get NTP peer states 
POST - Add NTP configuration into CONFIG DB.
PATCH - Update existing NTP configuraiton information in CONFIG DB.
DELETE - Delete a existing NTP configuration from CONFIG DB.
```

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### Configuration via CLI

| Test Name | Test Description |
| :-------- | :----- |
| Configure NTP server | Verify NTP servers are installed correctly in the configDB and reflected in the NTP peers |
| Delete NTP server | Verify NTP servers are installed correctly in the configDB and reflected in the NTP peers  |
| Configure NTP source| Verify NTP source is installed correctly in the configDB, NTP packets are transmitted and received over this source |
| Delete NTP source| Verify that NTP source is removed from the configDB, NTP packets are transmitted and received over the default interface|
| Configure NTP vrf| Verify that NTP vrf is installed correctly in the configDB and ntp service is running in the specified VRF|
| Delete NTP vrf| Verify that NTP vrf is removed from the configDB and ntp service is running in the default instance|
| show ntp associations | Verify ntp associations are displayed correctly |

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request.
Additional tests will be done to set NTP configuration at different levels of Yang models.

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done to get NTP configuration and NTP states at different levels of Yang models.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST request
Additional tests will be done to set NTP configuration at different levels of Yang models.


#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done to get NTP configuration and NTP states at different levels of Yang models.


# 10 Internal Design Information


