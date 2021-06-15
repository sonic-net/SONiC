# SONiC VLAN trunk all, except and none options support
Add support to configure allowed VLANs on trunk port using the options: "all", "except", "none" and *vlan-list* via KLISH CLI in SONiC Mgmt-Framework.
# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#Revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#1.1-requirements)
      * [1.1.1 Configuration and Management Requirements](#1.1.1-configuration-and-management-requirements)
    * [1.2 Design Overview](#1.2-design-overview)
       * [1.2.1 Basic Approach](#1.2.1-basic-approach)
       * [1.2.2 Container](#1.2.2-container)
  * [2 Functionality](#2-functionality)
    * [2.1 Target Deployment Use Case](#2.1-target-deployment-use-case)
    * [2.2 Functional Description](#2.2-functional-description)
  * [3 Design](#3-design)
    * [3.1 Overview](#3.1-overview)
    * [3.2 DB Changes](#3.2-db-changes)
      * [3.2.1 CONFIG DB](#3.2.1-config-db)
      * [3.2.2 APP DB](3.2.2-app-db)
      * [3.2.3 STATE DB](3.2.3-state-db)
    * [3.3 User Interface](3.3-user-interface)
      * [3.3.1 Data Models](3.3.1-data-models)
      * [3.3.2 CLI](3.3.2-cli)
        * [3.3.2.1 Configuration Commands](3.3.2.1-configuration-commands)
        * [3.3.2.2 Show Commands](3.3.2.2-show-commands)
          * [3.3.2.2.1 show running-config](3.3.2.3.1-show-running-config)
        * [3.3.2.3 IS-CLI Compliance](3.3.2.5-iscli-compliance)
      * [3.3.3 REST API Support](3.3.3-rest-api-support)
  * [4 Error Handling](5-error-handling)
  * [5 Unit Test](8-unit-test)


# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 01/04/2021  |   Haemanthi Sree K R, Tejaswi Goel     | Initial draft          |
| 0.2 | 01/11/2021  |   Haemanthi Sree K R, Tejaswi Goel     | v1.0                   |

# About this Manual
This document introduces trunk port allowed VLANs configuration via KLISH CLI using the options: all, except, none or *vlan-list*. And discusses the corresponding changes required in mgmt-framework. 
# Scope
Covers the backend mechanism required to support each command and the unit testcases.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| VLAN                     | Virtual Local Area Network          |

# 1 Feature Overview

Provide ability to configure allowed VLANs on trunk port using options "all", "except", "none" or *vlan-list*. 

## 1.1 Requirements

### 1.1.1 Configuration and Management Requirements
    
1. Support KLISH CLI "all" option to allow all VLAN IDs on trunk port. Port is added in all existing VLANs and any future VLAN that get created in the system, port is automatically added in this VLAN. 
2. Support KLISH CLI "except" option to allow all VLAN IDs except the specified VLAN IDs on trunk port. Any future VLAN that get created in the system except for the specified VLANs, port is automatically added in this VLAN. 
3. Support KLISH CLI "none" option to remove trunk port from all VLANs. Any future VLANs that get created in the system, will exclude this port now.
4. Support KLISH CLI option to directly specify allowed VLAN IDs list (*\<vlan-list\>*) without any other parameter, to add port to specified list of tagged VLANs. Existing tagged VLANs configuration on port will be replaced with the specified VLANs configuration.
5. Higher precedence to "untagged" VLAN config; i.e., if port is already tagged and untagged config is given then port's tagging_mode will be changed to untagged for the specified VLAN. And if port already untagged and tagged config is given then the port will remain untagged for the specified VLAN. 
6. Allow non-existing VLAN IDs configuration on port/portchannel. 
7. "show running config" to show all the allowed VLANs (existing and non-existing) configured on the interface.
8. Automatic addtion of members during VLAN creation; all interfaces having the VLAN config will be added as members during VLAN creation.
9. VLAN deletion will only remove the VLAN i.e the VLAN config on the port/portchannel is preserved in DB, so that when the VLAN gets re-created these members are automatically added back.
10. No L3 config will be allowed on interface even if non-existing VLAN is configured on interface. 

### 1.1.2 Scalability Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach

1. For supporting KLISH CLI "all" option, transaction will be a PATCH request with the VLAN range 1..4094.  
2. For supporting KLISH CLI "except" option, transaction will be a REPLACE request with the VLANs inclusive list i.e. allowed VLANs list excluding specified VLANs. 
3. For supporting KLISH CLI "none" option, trasaction will be a DELETE request to remove trunk port from all VLANs.  
4. For supporting KLISH CLI *vlan-list* option, transaction will be a POST request with the VLANs in *vlan-list*.
5. Changes in ConfigDB's PORT & PORTCHANNEL tables to store non-existing and existing VLAN IDs config on an interface.
6. To support automatic addition of members during VLAN creation, a "cache" will be maintained, caching trunk and access ports list for each VLAN. Cache will be automatically updated if any event in port's or portchannel's "tagged_vlans" and "access_vlan" fields in Config DB.

### 1.2.2 Container

* **management-framework** :
  * XML file changes for the new CLI options.
  * Python script changes to handle CLI request (actioner). CLI will internally do REST calls via openconfig yang.
  * OpenConfig YANG model changes to allow RPC implemenation for replacing VLANs. 
  * SONiC YANG model changes to add tagged_vlan leaf-list and access_vlan leaf in PORT and PORTCHANNEL table.
  * Transformer functions to convert the Openconfig yang configurations to Sonic-yang (Config-DB).

# 2 Functionality
## 2.1 Target Deployment Use Cases
Configure allowed VLANs on port via KLISH CLI.

## 2.2 Functional Description
Provide new KLISH CLI options: "all", "except", "none" & *vlan-list* to configure allowed VLANs on an interface. 

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to support new options for configuring allowed VLANs on trunk port.

## 3.2 DB Changes
### 3.2.1 CONFIG DB

* This feature will allow the users to perform trunk port allowed VLANs related configuration changes to CONFIG DB.
* New fields "tagged_vlans" leaf-list and "access-vlan" leaf added in PORT and PORTCHANNEL table to store VLAN configuration. 

### 3.2.2 APP DB
### 3.2.3 STATE DB

## 3.3 User Interface
### 3.3.1 Data Models
The following SONiC yang model changes are required to support all,except and none option for VLAN trunk config. 
* sonic-port.yang
* sonic-portchannel.yang
* openconfig-interfaces-ext.yang
```diff

module: sonic-port.yang

    +--rw sonic-port
       +--rw PORT
       |  +--rw PORT_LIST* [ifname]
       |     +--rw ifname                      string
       |     +--rw index?                      uint16
       |     +--rw speed?                      uint64
       |     +--rw fec?                        scommon:fec-mode
       |     +--rw valid_speeds?               string
       |     +--rw alias?                      string
       |     +--rw description?                string
       |     +--rw mtu?                        uint32
       |     +--rw lanes?                      string
       |     +--rw admin_status?               scommon:admin-status
       |     +--rw pfc_asym?                   string
       |     +--rw override_unreliable_los?    string
+      |     +--rw tagged_vlans*               string
+      |     +--rw access_vlan?                string
       +--ro PORT_TABLE
          +--ro PORT_TABLE_LIST* [ifname]
             +--ro ifname                -> /sonic-port/PORT/PORT_LIST/ifname
             +--ro index?                uint16
             +--ro lanes?                string
             +--ro mtu?                  uint32
             +--ro valid_speeds?         string
             +--ro alias?                string
             +--ro oper_status?          scommon:oper-status
             +--ro admin_status?         scommon:admin-status
             +--ro description?          string
             +--ro speed?                uint64
             +--ro port_load_interval?   uint16
             +--ro fec?                  scommon:fec-mode


module: sonic-portchannel
    +--rw sonic-portchannel
       +--rw PORTCHANNEL_GLOBAL
       |  +--rw PORTCHANNEL_GLOBAL_LIST* [keyleaf]
       |     +--rw keyleaf                    enumeration
       |     +--rw graceful_shutdown_mode?    mode
       +--rw PORTCHANNEL
       |  +--rw PORTCHANNEL_LIST* [name]
       |     +--rw name                       string
       |     +--rw admin_status?              scommon:admin-status
       |     +--rw mtu?                       uint32
       |     +--rw static?                    boolean
       |     +--rw min_links?                 uint8
       |     +--rw fallback?                  boolean
       |     +--rw fast_rate?                 boolean
       |     +--rw graceful_shutdown_mode?    mode
       |     +--rw description?               string
+      |     +--rw tagged_vlans*              string
+      |     +--rw access_vlan?               string
       +--rw PORTCHANNEL_MEMBER
       |  +--rw PORTCHANNEL_MEMBER_LIST* [name ifname]
       |     +--rw name      -> ../../../PORTCHANNEL/PORTCHANNEL_LIST/name
       |     +--rw ifname    -> /prt:sonic-port/PORT/PORT_LIST/ifname
       +--ro LAG_TABLE
       |  +--ro LAG_TABLE_LIST* [lagname]
       |     +--ro lagname                 string
       |     +--ro admin_status?           scommon:admin-status
       |     +--ro mtu?                    uint32
       |     +--ro active?                 boolean
       |     +--ro name?                   string
       |     +--ro oper_status?            scommon:oper-status
       |     +--ro traffic_disable?        boolean
       |     +--ro fallback_operational?   boolean
       |     +--ro speed?                  uint64
       |     +--ro port_load_interval?     uint16
       +--ro LAG_MEMBER_TABLE
          +--ro LAG_MEMBER_TABLE_LIST* [name ifname]
             +--ro name      -> ../../../LAG_TABLE/LAG_TABLE_LIST/lagname
             +--ro ifname    -> /prt:sonic-port/PORT/PORT_LIST/ifname
             +--ro status?   string
```
```diff

module: openconfig-interfaces-ext

  ...

  rpcs:
    +---x clear-counters
    |  +---w input
    |  |  +---w interface-param?   string
    |  +--ro output
    |     +--ro status?          int32
    |     +--ro status-detail?   string
+   +---x vlan-replace
+      +---w input
+      |  +---w ifname*     string
+      |  +---w vlanlist*   union
+      +--ro output
+         +--ro status?          uint32
+         +--ro status-detail?   string

```

### 3.3.2 CLI
#### 3.3.2.1 Configuration Commands

**switchport trunk allowed vlan {*vlan-list* | {add | except | remove} *vlan-list* | none | all}**

```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan
 <1..4094>  (-) or (,) separated individual VLAN IDs and ranges of VLAN IDs; for example, 20,70-100,142
  add     Configure trunking parameters on an interface
  all     configures port on all VLANs
  except  Configure trunking parameters on an interface
  none    Remove all trunking parameters on an interface
  remove  Remove trunking parameters on an interface
```
`switchport trunk allowed Vlan <vlan-list>`
```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan 20-30
sonic(conf-if-Ethernet16)#
```
`switchport trunk allowed Vlan all`
```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan all
sonic(conf-if-Ethernet16)#
```
`switchport trunk allowed Vlan except <vlan-list>`
```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan except
    (-) or (,) separated individual VLAN IDs and ranges of VLAN IDs; for example, 20,70-100,142

sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan except 1,10,20,2000-3000
sonic(conf-if-Ethernet16)#
```
`switchport trunk allowed Vlan none`
```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan none
sonic(conf-if-Ethernet16)#

```

#### 3.3.2.2 Show Commands
#### 3.3.2.2.1 show running-config
Show running-config <interface> will be enhanced to display all tagged & untagged VLAN IDs("existing and non-existing") configured on port. 

Here is the sample "show running-config" output for the interface:
<br>"switchport trunk allowed Vlan all" was executed on Ethernet 4
```
sonic# show running-configuration interface Ethernet 4
!
interface Ethernet4
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-4094
sonic#
```

#### 3.3.2.3 IS-CLI Compliance
All CLI commands mentioned above follows IS-CLI Compliance.

### 3.3.3 REST API Support
N/A

# 4 Error Handling
N/A

# 5 Unit Test and automation
The following test cases will be executed using KLISH CLI on Physical and Portchannel interfaces.

#### 5.1 Test cases for “all”, “except”, “none” and *vlan-list* options: 
##### 5.1.1 Test: switchport trunk allowed vlan all
* Verify config using 'show run-configuration' output. 
<br>*Sample output:*
```
sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 10
 switchport trunk allowed Vlan 1-4094
```
* Performance test by measuring the time taken for configuration.

##### 5.1.2 Test: switchport trunk allowed vlan "except" *vlan-list*
* Verify config using 'show run-configuration' output. 
<br>*Sample output:*
```
sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 1000-4000
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-999,4001-4094
```
* Performance test by measuring the time taken for configuration.

##### 5.1.3 Test: switchport trunk allowed vlan "none"
* Verify config using 'show run-configuration' output. 
<br>*Sample output:*
```
sonic(conf-if-EthernetX)#switchport trunk allowed vlan none
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
```
* Performance test by measuring the time taken for configuration.

##### 5.1.4 Test: switchport trunk allowed vlan *vlan-list* 
* Verify config using 'show run-configuration' output. 
<br>*Sample output:*
```
sonic(conf-if-EthernetX)#switchport trunk allowed vlan 100,1000-2000
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 10
 switchport trunk allowed Vlan 100,1000-2000
```
* Performance test by measuring the time taken for configuration.

#### 5.2 Functionality test 
##### 5.2.1 Test scenarios for “all”, “except”, “none” and *vlan-list* in combination with existing options: 

**Scenario 1:**
<br> Vlan 5 exists. 
<br> Step 1: sonic(conf-if-EthernetX)#switchport access Vlan 5
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 5
<br> Result: Port remains untagged in Vlan5, port is tagged in vlan 1-4,6-4094 
<br> Step 3: sonic(conf-if-EthernetX)#no switchport access vlan 
<br> Result: Port tagged in vlan 1-4,6-4094 
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-4,6-4094
sonic#
```

**Scenario 2:**
<br> Vlan 10 exists.
<br> Step 1: sonic(conf-if-EthernetX)#switchport access vlan 10 
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Result: Port remains untagged in vlan 10.
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 10
 switchport trunk allowed Vlan 1-4094
sonic#
```

**Scenario 3:**
<br> Vlan 10 exists.
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport access vlan 10
<br> Result: Port untagged port in vlan 10.
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 10
 switchport trunk allowed Vlan 1-4094
sonic#
```

**Scenario 4:**
<br> Vlan 20 does not exist.
<br> Step 1: sonic(conf-if-EthernetX)#switchport access vlan 20
<br> Result: Port untagged in vlan 20
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 20
sonic#
```
Verify: Check 'show vlan' output, should be empty since no VLAN exists.  
```
sonic# show Vlan

```
Step 2: Create Vlan20 - sonic(config)#interface vlan 20
<br> Verify member added during Vlan creation using 'show vlan' output.  
```
sonic(conf-if-Vlan20)# do show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
20         Inactive    A  EthernetX

```

**Scenario 5:**
<br> No vlan existing.
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Result: port tagged in 1-4094
<br> Step 2: sonic(conf-if-EthernetX)#switchport access vlan 20
<br> Result: port untagged in vlan 20 with pending tagged vlan 20 membership
<br> Verify: 'show run-configuration' & 'show vlan' output.  
<br> `Sample output:` show running-configuration interface Ethernet X
```
!
interface EthernetX
 mtu 9000
 speed 100000
 fec none
 no shutdown
 switchport access Vlan 20
 switchport trunk allowed Vlan 1-4094
```
<br> Step 3 - Create vlan 20: interface vlan 20
<br> `Sample output:` show Vlan 20
```
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
20         Inactive    A  EthernetX
sonic#
```
<br> Step 4: sonic(conf-if-EthernetX)#*no* switchport access vlan
<br> Result: port added back as tagged in vlan 20
<br> `Sample output:` show Vlan 20
```
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
20         Inactive    T  EthernetX
sonic#
```
<br> Step 5: sonic(conf-if-EthernetX)#*no* switchport trunk allowed vlan 20 
<br> Result: port tagged in 1-19,21-4094
<br> Verify: 'show run-configuration' output.  
<br> `Sample output:` 
```
sonic(conf-if-Ethernet4)# do show running-configuration interface Ethernet 4
!
interface Ethernet4
 mtu 9000
 speed 100000
 fec none
 no shutdown
 switchport trunk allowed Vlan 1-19,21-4094
sonic(conf-if-Ethernet4)#
```

**Scenario 6:**
<br> Vlan 20 does not exist.
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 20
<br> Step 2: sonic(conf-if-EthernetX)#switchport access vlan 20
<br> Step 3: sonic(config)#interface vlan 20
<br> Result: Port will be untagged in vlan 20
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 20
 switchport trunk allowed Vlan 1-19,21-4094
sonic#
```

**Scenario 7:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 5-7 
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan add 5
<br> Result: Port will be tagged in vlan 5
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-5,8-4094
sonic#
```

**Scenario 8:**
<br> Vlan 20 does not exist.
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 3: sonic(config)#interface vlan 20
<br> Result: Port tagged in vlan 1-4094
<br> Step 3: sonic(conf-if-EthernetX)#switchport access vlan 20
<br> Result: Port untagged in vlan 20
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport access Vlan 20
 switchport trunk allowed Vlan 1-4094
sonic#
```

**Scenario 9:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan add 1-11 (no VLAN existing)
<br> Step 2: sonic(conf-if-EthernetX)#switchport access vlan 11 (no VLAN existing)
<br> Step 3: sonic(config)#interface range create vlan 1-11
<br> Result: Port untagged in vlan 11 with pending tagged vlan 11 membership
<br> Step 4: sonic(conf-if-EthernetX)#no switchport access vlan
<br> Result: Port will be tagged in vlan 1-11
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-11
sonic#
```

**Scenario 10:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 20,30
<br> Result: Port will be tagged in vlan1-19,21-29,31-4094
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-19,21-29,31-4094
sonic#
```

**Scenario 11:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 1-10,20,30
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Result: Port will be tagged in vlan1-4094 
<br> Verify: 'show run-configuration' output. 
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-4094
sonic#
```

**Scenario 12:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan add 30
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 30
<br> Step 3: sonic(conf-if-EthernetX)#no switchport trunk allowed vlan 4000-4094
<br> Result: Port will be tagged in vlan1-29,31-3999
<br> Verify: 'show run-configuration' output.  
Sample show run-config output:
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-29,31-3999
sonic#
```

**Scenario 13:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan none
<br> Result: port has no vlan membership. 
<br> Verify: 'show run-configuration' output.  
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
sonic#
```

**Scenario 14:**
<br> Step 1: switchport trunk allowed vlan none
<br> Step 2: switchport trunk allowed vlan all
<br> Result: port tagged in vlan 1-4094
<br> Verify: 'show run-configuration' output.  
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-4094
sonic#
```
**Scenario 15:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan 1-20
<br> Result: Port tagged in Vlan1-20
<br> Verify: 'show run-configuration' output.  
```
sonic# show running-configuration interface Ethernet X
!
interface EthernetX
 mtu 9100
 speed 40000
 shutdown
 switchport trunk allowed Vlan 1-20
sonic#
```

**Scenario 16:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan 1-20
<br> Step 3: sonic(conf-if-EthernetX)#switchport access vlan 20
<br> Result: Port untagged in Vlan20
<br> Step 4: sonic(conf-if-EthernetX)#no switchport access vlan 
<br> Result: Port tagged in vlan1-20 
<br> Verify: 'show run-configuration' output.  

**Scenario 17**:
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan 1-20
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Result: Port tagged in vlan1-4094 
<br> Verify: 'show run-configuration' output.  

**Scenario 18:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 20-30
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan 20-30
<br> Result: Port tagged in vlan20-30 
<br> Verify: 'show run-configuration' output.  

**Scenario 19:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan 20-30
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 20-30
<br> Result: Port tagged in vlan 1-19,31-4094
<br> Verify: 'show run-configuration' output.  

**Scenario 20:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan all
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan remove 1-30
<br> Result: port tagged in vlan31-4094
<br> Verify: 'show run-configuration' output.  

**Scenario 21:**
<br> Step 1: sonic(conf-if-EthernetX)#switchport trunk allowed vlan except 1-10
<br> Step 2: sonic(conf-if-EthernetX)#switchport trunk allowed vlan remove 11 
<br> Result: Port tagged in Vlan12-4094
<br> Verify: 'show run-configuration' output.


##### 5.2.2 Test VLAN create and delete: 

**Scenario 1:** Automatic addition of members during VLAN creation
<br> Step 1 : Configure non-existing VLAN
```
(conf-if-Ethernet16)# switchport trunk allowed Vlan 12
sonic(conf-if-Ethernet16)# do show Vlan
sonic(conf-if-Ethernet16)#
```
<br> Step 2 : Create VLAN
```
sonic(config)# interface Vlan 12
```
<br> Step 2 : Verify VLAN config
`Klish CLI`
```
sonic(conf-if-Vlan12)# do show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
12         Inactive    T  Ethernet16
sonic(conf-if-Vlan12)#
```
`bcmsh`
```
drivshell>vlan show 12
vlan show 12
vlan 12 ports xe4 (0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000020000000000), untagged none (0x000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000) MCAST_FLOOD_UNKNOWN
drivshell>
```

**Scenario 2:** Delete VLAN and remove VLAN config
<br> Step 1 : VLAN delete
```
sonic(config)# do show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
12         Inactive    T  Ethernet16
```
```
sonic(config)# no interface Vlan 12
```
<br> Step 2: Verify 'show vlan' & 'show run-configuration <interface>' output.
```
sonic(config)# do show Vlan

sonic(config)#
sonic(config)# do show running-configuration interface Ethernet 16
!
interface Ethernet16
 mtu 9100
 speed 40000
 no shutdown
 switchport trunk allowed Vlan 12
sonic(config)#
```
<br> Step 3: Remove VLAN config on interface
```
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan none
sonic(conf-if-Ethernet16)# show configuration
!
interface Ethernet16
 mtu 9100
 speed 40000
 no shutdown
sonic(conf-if-Ethernet16)# do show running-configuration interface Ethernet 16
!
interface Ethernet16
 mtu 9100
 speed 40000
 no shutdown
```
**Scenario 3:** Configure non-existing VLAN12 on Ethernet16
```
sonic(config)# interface Ethernet16
sonic(conf-if-Ethernet16)# switchport trunk allowed Vlan 12
sonic(conf-if-Ethernet16)# do show Vlan 12

sonic(conf-if-Ethernet16)# show configuration
!
interface Ethernet16
 mtu 9100
 speed 40000
 no shutdown
 switchport trunk allowed Vlan 12
sonic(conf-if-Ethernet16)# exit
```
L3 config on an interface tagged in non-existing VLAN should return error:
```
sonic(conf-if-Ethernet16)# ip address 10.1.1.1/24
%Error: Tagged VLANs:12 configuration exists on interface: Ethernet16
sonic(conf-if-Ethernet16)#

```
Create VLAN12, Ethernet16 should be automatically added as member:
```
sonic(config)# interface Vlan 12
sonic(conf-if-Vlan12)# do show Vlan 12
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports
12         Inactive    T  Ethernet16

sonic(conf-if-Vlan12)#
```

#### 5.3 SONiC upgrade & downgrade with configuration persistence after installation. 
##### 5.3.1 Test image upgrade (migrating from 3.1.1 & 3.1.2 to 3.2.0) with configuration persistence after installation
* All trunk and access VLAN config cmds working fine. 
* No Warning/Error log must be shown.
* Verify "access_vlan" and "tagged_vlans@" attributes added in PORT table and PORTCHANNEL table for interfaces with VLAN config.
* Verify existing options "add" and "remove" to configure tagged VLANs work fine.
* Verify show version, sonic_installer list, show system status, show vlan, & show run-config output

##### 5.3.1 Test image downgrade (migrating from 3.2.0 to 3.1.2 & 3.1.1) with configuration persistence after installation
* All trunk and access VLAN config cmds working fine. 
* No Warning/Error log must be shown.
* Verify "access_vlan" and "tagged_vlans@" attributes removed from PORT table and PORTCHANNEL table for interfaces with VLAN config.
* Verify non-existing tagged/untagged VLANs config in 3.2.0 image has no impact when downgraded to previous versions.
* Verify show version, sonic_installer list, show system status, show vlan, & show run-config output

