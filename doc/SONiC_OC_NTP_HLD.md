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
| 0.1 | 05/03/2020 |   Bing Sun         | Initial version                   |
| 0.2 | 06/15/2020 |   Bing Sun         | Update based on comments          |
| 0.3 | 09/21/2020 |   Bing Sun         | Add dhcp behavior                 |
  
  
# About this Manual

This document introduces the support of NTP configuration using management framework. It also describes the corresponding backend ntp configuration and service restart upon configuration changes discussed here.

# Scope

This document covers NTP "configuration" and "show" commands based on the OpenConfig YANG model, as well as the backend mechanism required to support each command.
NTP unit tests are also included.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|          NTP             |  Network Time Protocol              |
|          ntpd            |  NTP Daemon                         |
| mgmt VRF                 | Management VRF                      |


# 1 Feature Overview

NTP stands for Network Time Protocol. It is used to synchronize the time of a computer or server to another server or reference time source.   

SONiC click CLI provides commands to add and delete the IP address of a remote NTP server. Multiple NTP servers can be configured, and both IPv4 and IPv6 are supported. SONiC click CLI also provides the show command (output of "ntpq -pn").   

This feature provides users the same capabilities via Management CLI, REST and gNMI using OpenConfig YANG models.
In addition, it provides users to configure NTP source interface and NTP vrf. For this release, only "mgmt" and "default" vrf can be configured as NTP vrf.

## 1.1 Requirements

### 1.1.1 Front end configuration and get capabilities

#### 1.1.1.1 add/delete NTP server      
Add/delete NTP server information in the Redis ConfigDB and in the ntp.conf file (NTP configuration file).   
The NTP server can be IPv4 address, IPv6 address , or a ntp pool name.   
Mutliple NTP servers can be configured.     
      
#### 1.1.1.2 add/delete NTP source interface
Add/delete the global NTP source interface in the Redis ConfigDB and in the ntp.conf file. The ip address of this interface will be used by ntpd as source ip for all NTP packets.     
Only one NTP source interface can be configured. 
Following interfaces can be used as NTP source interface when "mgmt" is not configured as NTP vrf.    
- Ethernet interface    
- PortChannel    
- Vlan interface    
- Loopback interfacee    
- eth0    
      
#### 1.1.1.3 add/delete VRF name
Add/delete the global NTP VRF information in the Redis ConfigDB. It is used by /etc/init.d/ntp script to start the ntpd in a specific VRF context.
For this release, only Management VRF and default instance are supported.         
        
#### 1.1.1.4 Get NTP association
This displays the output of "ntpq -np" command.  
    
#### 1.1.1.5 Overall Behavior related to NTP source interface and NTP vrf     
##### When mgmt VRF is configured      
a.if no ntp vrf is configured, ntp service starts in mgmt VRF context by default           
b.if "mgmt" is configured as NTP vrf, ntp service starts in mgmt VRF context        
c.if "default" is configured as NTP vrf, ntp service starts in default vrf context      
     
##### When mgmt VRF is not configured     
ntp service always starts in default vrf context      
      
##### NTP source interface related      
a.if NTP vrf is empty or "default", NTP source interface can be configured     
b.if NTP vrf is "mgmt", configuration of “ntp source-interface” will be rejected     
c.if NTP source interface is configured, configuration of "mgmt" as NTP vrf will be rejected     
d.if NTP source interface has ip configured, ip address of this interface will be used as source ip for all ntp packets     
e.if NTP source interface has no ip configured, it is treated as if no ntp source interface is configured     
f.if NTP vrf is "mgmt", eth0/mgmt interface ip will be used as source ip for all ntp packets by default     
 
    
### 1.1.2 Backend mechanisms to support configuration and get

#### 1.1.2.1 add/delete NTP server
This creates or deletes a NTP server entry in the Redis ConfigDB.

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
   
SONiC click CLI only supports IP address for NTP server. It can be extended to ntp pool name as well.   


#### 1.1.2.2 add/delete NTP source    

This creates or deletes a global NTP source interface entry in the Redis ConfigDB.      

```
  "NTP|global": {
    "type": "hash",
    "value": {
      "src_intf": "Ethernet36"
    }
  }
```

A change in this entry triggers hostcfgd to start the NTP configuration script, which in turn writes the ntp source interface to the ntp.conf and then restart the ntp service.   
Only one global NTP source entry is allowed.   
   
SONiC click CLI can be extended to include this configuration.
    

#### 1.1.2.3 add/delete NTP VRF      

This creates or deletes a global NTP vrf entry in the Redis ConfigDB. For this release, it can only be "mgmt" or "default".

```
  "NTP|global": {
    "type": "hash",
    "value": {
      "vrf": "mgmt"
    }
  }
```

A change in this DB entry triggers hostcfgd to restart ntp service.  
    
SONiC click CLI can be extended to include this configuration.   
    

#### 1.1.2.4 get NTP associations      

Transformer function issues "ntpq -p" command, parses the response and maps the outputs to the OpenConfig system YANG NTP states.      

### 1.1.3 Functional Requirements      

Provide management framework support to    
- configure NTP server   
- configure NTP source interface         
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
Only 1 source interface.
Ntpd runs in one VRF context, default vrf or mgmt vrf.
Multiple ntp servers supported.
    
### 1.1.7 Warm Boot Requirements         
NA

## 1.2 Design Overview                 

### 1.2.1 Basic Approach            
Implement NTP support using transformer in sonic-mgmt-framework.    

### 1.2.2 Container    
The front end code change will be done in management-framework container including:   
- XML file for the CLI   
- Python script to handle CLI request (actioner)   
- Jinja template to render CLI output (renderer)  
- front-end code to support "show running-configuration ntp" 
- OpenConfig YANG model for NTP openconfig-system.yang and openconfig-system-ext.yang   
- SONiC NTP model for NTP based on Redis DB schema of NTP   
- transformer functions to    
   * convert OpenConfig YANG model to SONiC YANG model for NTP related configurations   
   * convert from Linux command "ntpq -p" output to OpenConfig NTP state YANG model   

### 1.2.3 SAI Overview

# 2 Functionality

## 2.1 Target Deployment Use Cases 
Manage/configure NTP via gNMI, REST and CLI interfaces.         

## 2.2 Functional Description     
Provide CLI, gNMI and REST supports for NTP related configurations.    

## 2.3 Backend change to support new configurations     
Provide changes in hostcfgd, ntp.conf.j2 and /etc/init.d/ntp.          
SONiC click CLI enhancement if possible.      

## 2.4 Behavior when Management IP Address is acquired via DHCP
If the management IP address is acquired via DHCP, and if the NTP server option specifies the NTP server, /etc/dhcp/dhclient-exit-hooks.d/ntp script will generate the file /var/lib/ntp/ntp.conf.dhcp. This file is a copy of the default /etc/ntp.conf with a modified server list from the DHCP server. 
NTP daemon only uses one of the 2 files, and /var/lib/ntp/ntp.conf.dhcp takes precedence over the default /etc/ntp.conf. It is the existing behavior and is out of the scope of this HLD.

NTP source-interface and NTP vrf discussed in the HLD are only guaranteed to take effect on the static configured NTP servers.
For acquired NTP servers from DHCP server, NTP source-interface and NTP vrf will only take effect if /var/lib/ntp/ntp.conf.dhcp is generated based on the /etc/ntp.conf with user configured NTP source-interface.

Applying the configured NTP source-interface and NTP vrf to acquired NTP servers from the DHCP server is not a requirement for this release.
 
# 3 Design    

## 3.1 Overview    

Enhancing the management framework backend code and transformer methods to add support for NTP.

## 3.2 DB Changes

### 3.2.1 CONFIG DB      
This feature will allow users to make NTP configuration changes to CONFIG DB, and get NTP configurations.

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
   +--rw ntp
      |  +--rw config
      |  |  +--rw enabled?                           boolean
      |  |  +--rw enable-ntp-auth?                   boolean
+     |  |  +--rw oc-sys-ext:ntp-source-interface?   oc-if:base-interface-ref
+     |  |  +--rw oc-sys-ext:vrf?                    string
      |  +--ro state
      |  |  +--ro enabled?                           boolean
      |  |  +--ro enable-ntp-auth?                   boolean
      |  |  +--ro auth-mismatch?                     oc-yang:counter64
+     |  |  +--ro oc-sys-ext:ntp-source-interface?   oc-if:base-interface-ref
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
      |  +--rw servers
      |     +--rw server* [address]
+     |        +--rw address    -> ../config/address
+     |        +--rw config
+     |        |  +--rw address?            oc-inet:host
      |        |  +--rw port?               oc-inet:port-number
      |        |  +--rw version?            uint8
      |        |  +--rw association-type?   enumeration
      |        |  +--rw iburst?             boolean
      |        |  +--rw prefer?             boolean
+     |        +--ro state
+     |           +--ro address?                 oc-inet:host
      |           +--ro port?                    oc-inet:port-number
      |           +--ro version?                 uint8
      |           +--ro association-type?        enumeration
      |           +--ro iburst?                  boolean
      |           +--ro prefer?                  boolean
+     |           +--ro stratum?                 uint8
      |           +--ro root-delay?              uint32
      |           +--ro root-dispersion?         uint64
      |           +--ro offset?                  uint64
+     |           +--ro poll-interval?           uint32
+     |           +--ro oc-sys-ext:peerdelay?    decimal64
+     |           +--ro oc-sys-ext:peeroffset?   decimal64
+     |           +--ro oc-sys-ext:peerjitter?   decimal64
+     |           +--ro oc-sys-ext:selmode?      string
+     |           +--ro oc-sys-ext:refid?        inet:host
+     |           +--ro oc-sys-ext:peertype?     string
+     |           +--ro oc-sys-ext:now?          uint32
+     |           +--ro oc-sys-ext:reach?        uint8

module: sonic-system-ntp

+    +--rw sonic-system-ntp
+       +--rw NTP
+       |  +--rw NTP_LIST* [global_key]
+       |     +--rw global_key    enumeration
+       |     +--rw src_intf?     union
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

sonic(config)# ntp
  server            Configure NTP server
  source-interface  Configure NTP source interface to pick the source IP, used for the NTP packets
  vrf               Enable NTP on VRF

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

##### 3.6.2.1.3 Configure NTP source interface 

```
sonic(config)# ntp source-interface
  Ethernet          Ethernet interface
  Loopback          Loopback interface
  Management        Management Interface
  PortChannel       PortChannel interface
  Vlan              Vlan interface

sonic(config)# ntp source-interface Ethernet 48
sonic(config)#
sonic(config)#

sonic(config)# ntp source-interface Loopback 100
sonic(config)#
sonic(config)#
sonic(config)#
sonic(config)# ntp source-interface Management 0
sonic(config)#
sonic(config)#
sonic(config)#
sonic(config)# ntp source-interface PortChannel 100
sonic(config)#
sonic(config)#
sonic(config)#
sonic(config)# ntp source-interface Vlan 100
sonic(config)#

```
    
##### 3.6.2.1.4 Delete NTP source interface

```
sonic(config)# no ntp source-interface

```
    
##### 3.6.2.1.5 Configure NTP vrf

```
sonic(config)#
    vrf          Enabling NTP on a VRF

sonic(config)#ntp vrf
  mgmt     Enable NTP on management VRF
  default  Enable NTP on default VRF

```
    
##### 3.6.2.1.6 Delete NTP vrf

```
sonic(config)# no ntp
    vrf  Disable NTP on a VRF

sonic(config)# no ntp vrf

```
    
#### 3.6.2.2 Show ntp
```
sonic# show ntp
  associations  Display NTP associations
  global        Display NTP global configuration
  server        Display NTP server configuration

```
        
##### 3.6.2.2.1 show ntp associations 

```
sonic# show ntp associations
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*10.11.0.1       10.11.8.1        4 u   28   64    1    0.183    1.499   2.625
+2001:aa:aa::b   60.39.129.68    10 u   27   64    1    0.638  2171.31   0.411
+10.11.0.2       10.11.8.1        4 u   24   64    1    0.240  -13.957  12.786
* master (synced), # master (unsynced), + selected, - candidate, ~ configured

```
    
##### 3.6.2.2.2 Show configured ntp servers
```
sonic# show ntp server
--------------------------------
NTP Servers
--------------------------------
10.11.0.1
10.11.0.2
```
    
##### 3.6.2.2.3 Show global ntp configurations
```
sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP source-interface:   Ethernet24
NTP vrf:                default

``` 

##### 3.6.2.2.4 Show running-configuration

```
sonic(config)# ntp server 10.11.0.1
sonic(config)# ntp server pool.ntp.org
sonic(config)# ntp source-interface Ethernet 16
sonic(config)# do show running-configuration 
!
ntp server 10.11.0.1
ntp server pool.ntp.org
ntp source-interface Ethernet 16
!

sonic(config)# no ntp source-interface 
sonic(config)# ntp vrf mgmt 
sonic(config)# do show running-configuration 
!
ntp server 10.11.0.1
ntp server pool.ntp.org
ntp vrf mgmt
!

sonic(config)# ntp vrf default 
sonic(config)# do show running-configuration
!
ntp server 10.11.0.1
ntp server pool.ntp.org
ntp vrf default
!

```
    
#### 3.6.2.3 Debug Commands
```
From KLISH:

show ntp associations

show ntp server

show ntp global

```

```
From shell:

servcie ntp status

check /etc/ntp.conf

check /var/log/syslog and look for ntp

ifconfig lo

ifconfig lo-m

show mgmt-vrf

```
    
#### 3.6.2.4 IS-CLI Compliance

### 3.6.3 REST API Support
```
GET - Get existing NTP configuration information from CONFIG DB.
      Get NTP peer states
PUT  - Create NTP configuration into CONFIG DB. 
POST - Add NTP configuration into CONFIG DB.
PATCH - Update existing NTP configuraiton information in CONFIG DB.
DELETE - Delete a existing NTP configuration from CONFIG DB.
```
    
# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug

# 7 Warm Boot Support
NA      

# 8 Scalability

# 9 Unit Test

The unit-test for this feature will include:
#### Configuration via CLI

| Test Name | Test Description |
| :-------- | :----- |
| Configure NTP server | Verify NTP servers are installed correctly in the configDB and reflected in the NTP peers |
| Delete NTP server | Verify NTP server is deleted from the configDB and reflected in the NTP peers  |
| Configure NTP source interface| Verify NTP source interface is installed correctly in the configDB, NTP packets are transmitted and received over this source |
|                               | Verify that NTP source interface cannot be configured if NTP vrf is mgmt|
| Delete NTP source interface| Verify that NTP source interface is removed from the configDB, NTP packets are transmitted and received over the default interface|
| Configure NTP vrf| Verify that NTP vrf is installed correctly in the configDB and ntp service is running in the specified VRF|
|                  | Verify that only default and mgmt can be configured as NTP vrf|
|                  | Verify that mgmt cannot be configured as NTP vrf if NTP source interface is configured|
| Delete NTP vrf| Verify that NTP vrf is removed from the configDB and ntp service is running in the default instance|
| show ntp associations | Verify ntp associations are displayed correctly |
| show ntp server       | Verify ntp servers are displayed correctly |
| show ntp global       | Verify ntp global configurations are displayed correctly |

#### Configuration via gNMI

Same test as CLI configuration Test but using gNMI request.
Additional tests will be done to set NTP configuration at different levels of YANG models.

#### Get configuration via gNMI

Same as CLI show test but with gNMI request, will verify the JSON response is correct.
Additional tests will be done to get NTP configuration and NTP states at different levels of YANG models.

#### Configuration via REST (POST/PUT/PATCH)

Same test as CLI configuration Test but using REST POST/PUT/PATCH request.
Additional tests will be done to set NTP configuration at different levels of YANG models.


#### Get configuration via REST (GET)

Same as CLI show test but with REST GET request, will verify the JSON response is correct.
Additional tests will be done to get NTP configuration and NTP states at different levels of YANG models.
    

# 10 Internal Design Information


