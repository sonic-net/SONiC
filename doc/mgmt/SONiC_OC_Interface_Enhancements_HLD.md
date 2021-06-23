# SONiC Interface Enhancements

# High Level Design Document
# Table of Contents
- [1 Feature Overview](#1-feature-overview)
    - [1.1 Target Deployment Use Cases](#11-target-deployment-use-cases)
    - [1.2 Requirements](#12-requirements)
    - [1.3 Design Overview](#13-design-overview)
        - [1.3.1 Basic Approach](#131-basic-approach)
        - [1.3.2 Container](#132-container)
        - [1.3.3 SAI Overview](#133-sai-overview)
- [2 Functionality](#2-functionality)
- [3 Design](#3-design)
    - [3.1 Overview](#31-overview)
    - [3.2 DB Changes](#32-db-changes)
        - [3.2.1 CONFIG DB](#321-config-db)
        - [3.2.2 APP DB](#322-app-db)
        - [3.2.3 STATE DB](#323-state-db)
        - [3.2.4 ASIC DB](#324-asic-db)
        - [3.2.5 COUNTER DB](#325-counter-db)
        - [3.2.6 ERROR DB](#326-error-db)
    - [3.3 Switch State Service Design](#33-switch-state-service-design)
        - [3.3.1 Orchestration Agent](#331-orchestration-agent)
        - [3.3.2 Other Processes](#332-other-processes)
    - [3.4 SyncD](#34-syncd)
    - [3.5 SAI](#35-sai)
    - [3.6 User Interface](#36-user-interface)
        - [3.6.1 Data Models](#361-data-models)
        - [3.6.2 CLI](#362-cli)
        - [3.6.3 REST API Support](#363-rest-api-support)
        - [3.6.4 gNMI Support](#364-gnmi-support)
     - [3.7 Warm Boot Support](#37-warm-boot-support)
     - [3.8 Upgrade and Downgrade Considerations](#38-upgrade-and-downgrade-considerations)
     - [3.9 IS-CLI Compliance](#39-is-cli-compliance)
- [4 Serviceability and Debug](#6-serviceability-and-debug)
- [5 Scalability](#7-scalability)
- [6 Platform](#8-platform)
- [7 Unit Test and automation](#8-unit-test)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 06/23/2021|  Tejaswi Goel        | Initial version                   |

# About this Manual
This document provides functional and design information about "shutdown" support for VLAN and Loopback interfaces.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| VLAN       |  Virtual Local Area Network |
| LAG        |  Link aggregation |

# 1 Feature Overview
#### VLAN

* Add support for admin state configuration to bring the VLAN interface up or down using KLISH CLI commmand -"[no] shutdown", REST or gNMI. 
* VLAN interface will be Operationally down when admin state is down, irrespective of the autostate setting and members oper state.  
* When the VLAN interface is "administratively down" or "shutdown", the L3 functions within that VLAN will be disabled, and L2 traffic will continue to flow.
* By default, the VLAN's state in kernel is down and changes to up only when first port/LAG in the VLAN is oper up or autostate is disabled and admin state is up.

#### Loopback

* Add support for admin state configuration via KLISH CLI option-"[no] shutdown", REST or gNMI. 
* By default, admin state & oper state is up. 

## 1.1 Target Deployment Use Cases
Enable/disable VLAN and Loopback interfaces via gNMI, REST or KLISH CLI.

## 1.2 Requirements

### 1.2.1 Functional requirements
1. Provide management framework capability to handle admin state configuration for VLAN & Loopback interfaces.

### 1.2.2 Configuration and Management Requirements

#### 1.2.2.1 KLISH requirements

1. To administratively bring the VLAN and Loopback interface down, use "shutdown" command.
2. To return the interface to its default admin state, use "no shutdown".
3. The above configurations should be displayed as part of a show command.  

## 1.3 Design Overview

### 1.3.1 Basic Approach
#### 1.3.1.1 VLAN

1. The VLAN table in the CONFIG_DB supports admin state up/down parameter.
2. The VlanMgr to be enhanced to populate the APP_DB with the admin state up/down.
3. The orchagent to be enhanced to update VLAN's oper state based on admin state. 
   The contributors to the the operational status are as follows: 
   - Admin state.
   - Autostate.
   - Physical Port members.
   - LAG members.
4. When the configuration changes from admin state up to down the operational status will change to operationally down. If the state were to be already operationally down then it will be a no-op. 
5. When the configuration changes from admin down to up the operational status will change to operationally up based on autostate and members operational state.  
6. For the VLAN state in kernel, the existing mechanism to notify the VlanMgr about the operational status will be reused. 

#### 1.3.1.2 LOOPBACK
1. Update LOOPBACK table in the CONFIG_DB to support admin state up/down parameter.
2. The LOOPBACK_TABLE in APP_DB already supports admin state up/down parameter.
3. The oper status will be controlled by the admin status. 
4. When the configuration changes from admin state up to down the operational status will change to operationally down.  
5. When the configuration changes from admin down to up the operational status will change to operationally up.   

### 1.3.2 Container
* **swss container** : 
  * VlanMgr and Orchagent changes to also consider admin status while setting oper status.
* **management-framework** :
  * CLI XML & Jinja-template changes to support CLI-style configurations and relevant show commands.
  
### 1.3.3 SAI Overview
N.A

# 2 Functionality
As Described in section 1.2

# 3 Design
## 3.1 Overview
As described in section 1.3

## 3.2 DB Changes

### 3.2.1 CONFIG DB
**VLAN table**
* No change.

**LOOPBACK table**
* Producer: Mangement framework
* Consumer: VlanMgr
* Description: Update existing table to store 'admin_status' configuration.
* Schema:
```
;Existing table
;defines Loopback. Store admin state configuration 
;
;Status: stable

key = LOOPBACK_TABLE|LOOPBACK_NAME ;
admin_status = "up"/"down" ; admin status
```

### 3.2.2 APP DB
**VLAN_TABLE** 
* No change.

**LOOPBACK_TABLE** 
* No change.

### 3.2.3 STATE DB
N/A
### 3.2.4 ASIC DB
N/A
### 3.2.5 COUNTER DB
N/A
### 3.2.6 ERROR DB
N/A

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
As in sec 1.3
### 3.3.2 Other Processes 
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface

### 3.6.1 Data Models

#### 3.6.1.1 SONiC Yang
#### VLAN
1. sonic-vlan.yang
* Containers VLAN and VLAN_TABLE already have leaf admin status as below:
```
leaf admin_status {
    type scommon:admin-status;
}
```
#### LOOPBACK
1. sonic-loopback.yang
* Update containers LOOPBACK and LOOPBACK_TABLE with leaf admin status as below:
```
leaf admin_status {
    type scommon:admin-status;
}
```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands

#### VLAN
```
sonic(conf-if-Vlan100)# [no] shutdown
sonic(conf-if-range-vl**)# [no] shutdown
```
#### LOOPBACK
```
sonic(conf-if-lo10)# [no] shutdown
```

#### 3.6.2.2 Show Commands

#### VLAN
* "show vlan" displays the Vlan Interface’s operational status.
```
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports        AutoState
100        Inactive    T  Ethernet0   Enable
                       T  Ethernet1
101        Active      T  Ethernet1   Disable
```
* "show interface vlan" displays both the Admin & Oper status
```
sonic(config)# do show interface Vlan 1
Vlan1 is up, line protocol is down
Mode of IPV4 address assignment: not-set
Mode of IPV6 address assignment: not-set
Interface IPv6 oper status: Disabled
IP MTU 9100 bytes
sonic(config)#
```
* "show configuration" to display "shutdown" configuration.  
```
sonic(config)# do show running-configuration interface Vlan 11
!
interface Vlan11
 shutdown
```

#### LOOPBACK
* "show interface Loopback" to display both admin status and oper status, currently only oper status is shown.
```
sonic#show interface Loopback 10
Loopback 10 is up, line protocol is up
Mode of IPV4 address assignment: not-set
Mode of IPV6 address assignment: not-set
Interface IPv6 oper status: Disabled

```
* "show configuration" to display "shutdown" configuration.  
```
sonic(config)# do show running-configuration interface loopback 11
!
interface Loopback 11
 shutdown
```

#### 3.6.2.3 Exec Commands
N.A

### 3.6.3 REST API Support

#### 3.6.3.1 SONiC yang
#### VLAN
```
 PATCH and GET - /restconf/data/sonic-vlan:sonic-vlan/VLAN/VLAN_LIST=Vlan100/admin_status
 GET - /restconf/data/sonic-vlan:sonic-vlan/VLAN_TABLE/VLAN_TABLE_LIST=Vlan100/admin_status
```
#### Loopback
```
 PATCH and GET - /restconf/data/sonic-loopback:sonic-loopback/LOOPBACK/LOOPBACK_LIST=Loopback100/admin_status
 GET - /restconf/data/sonic-loopback:sonic-loopback/LOOPBACK_TABLE/LOOPBACK_TABLE_LIST=Loopback100/admin_status
```

#### 3.6.3.2 OpenConfig yang 
#### VLAN & Loopback
```
 PATCH - openconfig-interfaces:interfaces/interface=${intf_name}/config/enabled 
 GET - openconfig-interfaces:interfaces/interface=${intf_name}/state/enabled
```
### 3.6.4 gNMI Support
gNMI operations will be supported using OC yang configuration objects & state objects.

## 3.7 Warm Boot Support
No impact to warm boot support due to this enhancement. 

## 3.8 Upgrade and Downgrade Considerations
By default the admin state is up. Upgrade from an earlier release will have all the 
configured VLANs in an admin state up state. There will be no change in behavior from the
earlier releases. The user has an option to change the admin state configuration post upgrade.

## 3.9 IS-CLI Compliance
All CLI commands mentioned above follows IS-CLI Compliance.

# 4 Serviceability and Debug
Existing Logging mechanisms and show commands will help in debuggability.

# 5 Scalability
N.A

# 6 Platform
Applicable on all platforms.

# 7 Unit Test and automation
* Test cases are to be automated with spytest.

### 7.1 VLAN

#### 7.1.1 Verify KLISH CLI `[no] shutdown` configuration

* Verify VLAN's state using 'show vlan', 'show config' and 'show interface vlan' output.

|S.No | Testcase | Testcase description |
| :------ | :----- | :----- |
| 1 | Create VLAN | Verify VLAN's state is admin up and oper down |
| 2 | "shutdown" the VLAN interface | Verify VLAN's admin state is down and oper state is down |
| 3 | "no shutdown" the VLAN interface, with no members added to VLAN and autostate enabled | Verify VLAN's admin state shown as up and oper state shown as down |
| 4 | Set autostate disabled and shutdown VLAN | Verify VLAN state changes to admin down and oper down |
| 5 | Set autostate disabled and "no shutdown" the VLAN | Verify VLAN state changes to admin up and oper up |
| 6 | With autostate enabled & atleast 1 member of VLAN as oper up, "shutdown" the VLAN | Verify VLAN's state is admin down and oper down |
| 7 | With autostate enabled & atleast 1 member of VLAN as oper up, "no shutdown" the VLAN | Verify VLAN's state is admin up and oper up |
| 8 | Add active port/port-channel to VLAN, then create VLAN | Verify VLAN's state is admin up and oper up |
| 9 | Add active port/port-channel to VLAN, then create VLAN and "shutdown" the VLAN | Verify VLAN's state is admin down and oper down |
| 10 | Run "shutdown" on a range of VLAN interfaces | Verify VLAN's state |

#### 7.1.2 Verify VLAN's state in kernel 
* Configuration done using KLISH CLI
* Verify VLAN's state using Linux cmds. 

|S.No | Testcase | Testcase description |
| :------ | :----- | :----- |
| 1 | Create VLAN using KLISH CLI | Verify VLAN state is down |
| 2 | With autostate enabled, "shutdown" the VLAN interface | Verify VLAN's state is down |
| 3 | With autostate enabled, "no shutdown" the VLAN interface and add active member | Verify VLAN's state is up & running |
| 4 | Set autostate disabled & "shutdown" the VLAN interface | Verify VLAN's state is down |
| 5 | Set autostate disabled & "no shutdown" the VLAN interface | Verify VLAN's state is up & running |
| 6 | Add active port to VLAN, then create VLAN | Verify VLAN state is up & running |
| 7 | Add active port to VLAN, then create VLAN and "shutdown" | Verify VLAN's state is down |

#### 7.1.4 Test L3 functioanlity 
|S.No | Testcase | Testcase description | 
| :------ | :----- | :----- |
| 1 | Configure ip address in VLAN interface, then "shutdown" the already active VLAN interface | Verify network address is not in the IP routing table and it's IP cannot be pinged. |
| 2 | Configure ip address in VLAN interface, then "no shutdown" the VLAN interface | Verify VLAN is admin up and oper up, and network address is in the IP routing table. |

#### 7.1.5 Verify reboot, config-reload with admin state up and down.

### 7.2 LOOPBACK

#### 7.2.1 Verify KLISH CLI `[no] shutdown` configuration
* Verify config using `show interface loopback run-config` and `show interface loopback <id>` output.

|S.No | Testcase | Testcase description |
| :------ | :----- | :----- |
| 1 | Create Loopback | Verify the state is admin up and oper up |
| 2 | "shutdown" the loopback interface | Verify VLAN's state is admin down and oper down |
| 3 | "no shutdown" the loopback interface | Verify VLAN's state is admin up and oper up  & Loopback interface routing is working |

#### 7.2.2 Verify Loopback's state in kernel.
* Configuration done using KLISH CLI
* Verify state using Linux cmds. 

#### 7.2.3 Test L3 functioanlity 
|S.No | Testcase | Testcase description | 
| :------ | :----- | :----- |
| 1 | Configure ip address, then "shutdown" the Loopback interface | Verify network address not in the IP routing table and not able to ping the IP address |
| 2 | Configure ip address, then "no shutdown" the Loopback interface | Verify network address in the IP routing table and can be pinged |

#### 7.2.4 Verify reboot, config-reload with admin state up and down.


