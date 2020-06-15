

﻿# Warm restart feature support 

Implement CLI, REST and gNMI interface to configure and manage warm restart functionality.
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
| Rev  |    Date    |      Author      | Change Description |
| :--: | :--------: | :--------------: | ------------------ |
| 0.1  | 05/21/2020 | Arul Jeniston Mc | Initial version    |

# About this Manual
This document provides information about configuring and managing warm restart data.
# Scope
This document covers the "configuration" and "show" commands supported in warm-restart based on newly added SONiC yang file and unit test cases.
It does not include the implementation details of warm-restart feature.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term** | **Meaning**                   |
| -------- | ----------------------------- |
| BGP      | Border Gateway Protocol       |
| CLI      | Command Line Interface        |
| CLISH    | Command Line Interface SHell  |
| EOIU     | End-of-Initial Update         |
| gNMI     | gRPC Network Management       |
| REST     | Representation State Transfer |
| SWSS     | Switch State Service          |

# 1 Feature Overview

Add support to configure and show warm-restart configurations and states via CLI, REST and gNMI using sonic, open-config yang data model and sonic-mgmt-framework container


## 1.1 Requirements

Provide management framework capabilities to handle:
  Enable/Disable warm-restart for bgp,swss,teamd,system services.
  show the configuration and states of WarmRestart for every service.
  Configure and show the per service WarmRestart attributes.

### 1.1.1 Functional Requirements

Provide management framework support to existing SONiC capabilities with respect to WarmRestart

### 1.1.2 Configuration and Management Requirements

- IS-CLI style configuration and show commands
- REST API support
- gNMI support
Details described in Section 3.

TBD

### 1.1.3 Scalability Requirements
key scaling factors - N/A
### 1.1.4 Warm Boot Requirements
N/A
## 1.2 Design Overview
### 1.2.1 Basic Approach
Provide transformer methods in sonic-mgmt-framework container for WarmRestart handling.

### 1.2.2 Container
All code changes will be done to management-framework and telemetry container. We make CLISH changes in management-framework and yang and transformer changes in mgmt-common repository.

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
Manage/configure WarmRestart via GNMI, REST and CLI interfaces
## 2.2 Functional Description
Provide CLI, gNMI and REST support for WarmRestart related commands handling

# 3 Design
## 3.1 Overview
Enhancing the management framework backend code and transformer methods to add support for WarmRestart Handling
## 3.2 DB Changes
A new table WARM_RESTART_ENABLE is added in config DB to store enable/disable state.

### 3.2.1 CONFIG DB

The following WARM_RESTART table values are configured. 

```
redroot@sonic:~# redis-cli
127.0.0.1:6379> select 4
OK
127.0.0.1:6379[4]> keys "WARM*"
1) "WARM_RESTART|teamd"
2) "WARM_RESTART|swss"
3) "WARM_RESTART|bgp"

127.0.0.1:6379[4]> hgetall "WARM_RESTART|teamd"
1) "teamsyncd_timer"
2) "100"

```

Added a new table WARM_RESTART_ENABLE to config DB to configure enable/disable state of BGP,SWSWS, teamd, system services.

```
127.0.0.1:6379[4]> hgetall "WARM_RESTART_ENABLE|teamd"
1) "enable"
2) "true"

127.0.0.1:6379[4]> hget "WARM_RESTART_ENABLE|teamd" enable
"true

```

### 3.2.2 APP DB

### 3.2.3 STATE DB

The following key values are read from STATE_DB.
WARM_RESTART_TABLE and WARM_RESTART_ENABLE_TABLE tables are present in STATE_DB.



```
redroot@sonic:~# redis-cli
127.0.0.1:6379> select 6
OK
127.0.0.1:6379[6]> keys "WARM*"
 1) "WARM_RESTART_TABLE|portmgrd"
 2) "WARM_RESTART_TABLE|teamsyncd"
 3) "WARM_RESTART_ENABLE_TABLE|system"
 4) "WARM_RESTART_TABLE|vlanmgrd"
 5) "WARM_RESTART_TABLE|vrrpsyncd"
 6) "WARM_RESTART_TABLE|gearsyncd"
 7) "WARM_RESTART_TABLE|portsyncd"
 8) "WARM_RESTART_ENABLE_TABLE|bgp"
 9) "WARM_RESTART_TABLE|iphelpermgr"
10) "WARM_RESTART_TABLE|orchagent"
11) "WARM_RESTART_TABLE|stpmgrd"
12) "WARM_RESTART_TABLE|intfmgrd"
13) "WARM_RESTART_ENABLE_TABLE|swss"
14) "WARM_RESTART_TABLE|bgp"
15) "WARM_RESTART_TABLE|dropmgrd"
16) "WARM_RESTART_TABLE|ifamgrd"
17) "WARM_RESTART_TABLE|xcvrd"
18) "WARM_RESTART_TABLE|l2mcmgrd"
19) "WARM_RESTART_TABLE|vrrpmgrd"
20) "WARM_RESTART_TABLE|vxlanmgrd"
21) "WARM_RESTART_TABLE|fdbsyncd"
22) "WARM_RESTART_TABLE|vrfmgrd"
23) "WARM_RESTART_TABLE|teammgrd"
24) "WARM_RESTART_TABLE|udldmgrd"
25) "WARM_RESTART_TABLE|nbrmgrd"
26) "WARM_RESTART_TABLE|neighsyncd"
27) "WARM_RESTART_TABLE|aclsvcd"
28) "WARM_RESTART_TABLE|natsyncd"
29) "WARM_RESTART_TABLE|syncd"
```

#### 3.2.3.1 SYNC CONFIG DB data with STATE DB

WARM_RESTART_ENABLE_TABLE table has configuration data in 'state' DB which doesn't survive the reboot. Since it is a configuration data, we added a new table (WARM_RESTART_ENABLE_TABLE) to config DB and sync this table data to 'State' DB table.  This data syncing is done from hostcfgd daemon that runs in native host. 

### 3.2.4 ASIC DB

### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
N/A

## 3.4 SyncD
N/A

## 3.5 SAI
N/A

## 3.6 User Interface
### 3.6.1 Data Models



List of yang models required for warm-restart feature management

1. [sonic-warmrestart.yang](#3.6.1.1-sonic-yang)
2. [openconfig-warmrestart.yang](#3.6.1.4-oc-yang)


###### 3.6.1.1 SONIC yang

```
$ cat sonic-warmrestart.yang
module sonic-warmrestart {
    namespace "http://github.com/Azure/sonic-warmrestart";
    prefix prt;

    import sonic-common {
        prefix scommon;
    }

    import sonic-extension {
        prefix sonic-ext;
    }

    organization
        "SONiC";

    contact
        "SONiC";

    description
        "SONIC WARMRESTART";

    revision 2020-05-18 {
        description
            "Initial revision.";
    }


    container sonic-warmrestart {        
        container WARM_RESTART_TABLE {
            config false;
            list WARM_RESTART_TABLE_LIST {
                key "module";

                leaf module {
                    type string;
                }

                leaf restore_count {
                    type uint16;
                }

                leaf state {
                    type scommon:mode-enable;
                }
            }
        }

        container warm-restart_ENABLE_TABLE {
             config false;
             list warm-restart_ENABLE_TABLE_LIST {
                key "module";

                leaf module {
                    type string;
                }

                leaf enable {
                    type boolean;
                    default "false";
                }
            }               
        }

        container warm-restart {

             list warm-restart_LIST {
                key "module";

                leaf module {
                    type string;
                }

                leaf bgp_eoiu {
                    when "../module = 'bgp'";
                    type boolean;
                    default "false";
                }

                leaf bgp_timer {
                    when "../module = 'bgp'";
                    type uint16;
                }

                leaf teamsyncd_timer {
                    when "../module = 'teamd'";
                    type uint16;
                }
                leaf neighsync_timer {
                    when "../module = 'swss'";
                    type uint16;
                }

                leaf enable {
                    type boolean;
                    default "false";
                }
            }
        }
    }
}

```

######   3.6.1.4 OC yang

```

module openconfig-warmrestart {

  yang-version "1";

  // namespace
  namespace "http://openconfig.net/yang/warmrestart/extensions";

  prefix "oc-wmr";

  //import some basic types
  import openconfig-extensions { prefix oc-ext; }

  // meta
  organization "OpenConfig working group";

  contact
    "OpenConfig working group
    netopenconfig@googlegroups.com";

  description
    "Warm Boot is the process to restart the switch driver daemon 
    without affecting data plane. Primary requirement of warm boot 
    to avoid any data plane traffic disruption during the warm boot.  
    Control plane traffic will be discarded by NPU since the CPU is
    not ready to receive packet during warmboot.";

  oc-ext:openconfig-version "1.0.0";

  revision "2020-06-09" {
    description
      "OpenConfig initial version";

    reference "1.0.0";
  }

  // OpenConfig specific extensions for module metadata.
  oc-ext:regexp-posix;
  oc-ext:catalog-organization "openconfig";
  oc-ext:origin "openconfig";


  typedef enable-module-type {

    type enumeration {

      enum BGP {
       description
         "BGP module";
      }

      enum TEAMD {
       description
         "Teamd module";
      }

      enum SWSS {
       description
        "SWSS module";
      }
    }
    description
      "The Modules supported in warmrestart";
  }

  typedef timer-submodule-type {
    
    type enumeration {

      enum BGP {
       description
         "The submodule of the BGP module";
      }

      enum TEAMSYNCD {
        description
          "The submodule of teamd module";
      }

      enum NEIGHSYNCD {
        description
          "The submodule of SWSS module";
      }
    }
    description
      "The submodules types of the modules supports in warmrestart";
  }

  grouping warmrestart-enable-system {
    description
      "Warmrestart system enable/disable";

    leaf enable {
      type boolean;

      description 
        "Enable or disable the system level";
    }
  }

  grouping warmrestart-enable-bgp-eoiu {
    description
      "Enable/disable the End-of-Initial Update (EOIU) for BGP";

    leaf bgp-eoiu {
      type boolean;

      description
        "Enable/disable the End-of-Initial Update (EOIU) for BGP";
    }
  }

  grouping warmrestart-module-enable {

    description
      "Module level warmrestart enable/disable";

    leaf enable {
      type boolean;

      description
        "Enable or disable a module in warmrestart";

    }
  }

  grouping warmrestart-submodule-timer-value {
    description 
     "Timer value for submodule";

    leaf value {
     type uint32 {
       range "1..9999";
     }

     description
       "Timer value for the submodule";
    } 
  }

  grouping warmrestart-enable-system-eoiu {
    description
      "Enable the warmrestart for system level and BGP EOIU";

    container config {
      description
        "Configure the values for system warmrestart and BGP EOIU.";

      uses warmrestart-enable-system;
      uses warmrestart-enable-bgp-eoiu;
    }

    container state {
      config false;

      description
        "Get the values for system warmrestart and BGP EOIU.";

        uses warmrestart-enable-system;
        uses warmrestart-enable-bgp-eoiu;
    }
  }

  grouping warmrestart-config-module-enable {
    description 
      "Enable warmrestart fot the module";

    container enable-warmrestart {
      description
        "Enclosing the container for the list of modules";

      list modules {
        key "module";

        description
           "The list of modules associated with the warmrestart";

        leaf module {

          type leafref {
            path "../config/module";
          }
          description
            "Name of the module";
        }

        container config {
          description
            "Configure the enable or disbale to the module";
             
          leaf module {
            type enable-module-type;
            description
              "Name of the module";
          }

          uses warmrestart-module-enable;

        }

        container state {
          config false;
          description
            "Operatiaonal data of state of the module";

          leaf module {
            type enable-module-type;
            description
              "Name of the module";
          }

          uses warmrestart-module-enable;

        } 
      }
    }
  }

  grouping warmrestart-config-submodule-timer {
    description 
      "Warmrestart configure timer for submodule ";

    container timers {
      description
        "Enclosing container for the list of submodule";

      list timer {
        key "submodule";

        leaf submodule {
          type leafref {
            path "../config/submodule";
          }
          description
            "Submodule name to config the timer";
        }

        container config {
          description
            "Configure the timer value of a submodule";

          leaf submodule {
            type timer-submodule-type;

            description
              "The submodule name of the Module";
          }

          uses warmrestart-submodule-timer-value;
        }

        container state {
          config false;
          description
            "Configure the timer value of a submodule";

          leaf submodule {
            type timer-submodule-type;

            description
              "The submodule name of the Module";
          }

          uses warmrestart-submodule-timer-value;
        }

        description
          "List of the submodule to configure timer value";
      }
    }
  }

  grouping warmrestart-submodule-state-data {
    description
      "Submodule state and restore count";

    leaf submodule {
      type string;

      description
        "The submodule name";
    }

    leaf restore-count {
      type uint16;

      description
        "The restore count value";
    }

    leaf state {
      type string;

      description
        "The current state of warmrestart of the submodule";
    }
  }

  grouping warmrestart-submodule-status {
    description 
      "Warmrestart submodule state data.";

    container status {
      description
        "Enclosing the list of submodule for state and restore count";

      list submodules {
        config false;

        description
          "Enclosing the list of submodule for state and restore count";

        container state {
          description
            "Get the state and restore count of  submodule";
          uses warmrestart-submodule-state-data; 
        }
      }
    }
  }
 
  grouping warmrestart-top {  
    description
      "Top level warmrestart data containers";

    container warmrestart {
      description
        "Enclosing container for warmrestart related configuration and
         operational state data";
        
      uses warmrestart-enable-system-eoiu;
      uses warmrestart-config-module-enable;
      uses warmrestart-config-submodule-timer;
      uses warmrestart-submodule-status;

    }
  }

  uses warmrestart-top;
}

```

### 3.6.2 CLI

#### 3.6.2.1 Configuration Commands

##### Config Help

```
sonic(config)# ?
......
......
  warm-restart      Warmrestart configruation

sonic(config)# warm-restart ?
  bgp               Warm restart BGP configuration
  swss              Warm restart SWSS configuration
  system            Warm restart system configruation
  teamd             Warm restart teamd configuration

```

##### Configure warmrestart for a service

```
sonic(config)# warm-restart bgp ?
  enable            Enable warmrestart for BGP service
  eoiu              End-of-initial update
  timer             Set warmrestart timer

sonic(config)# warm-restart teamd ?
  enable            Enable warm restart for teamd service
  timer             Set warmrestart timer

sonic(config)# warm-restart swss ?
  enable            Enable warm restart for SWSS service
  timer             Set Warmrestart timer

sonic(config)# warm-restart system ?
  enable            Enable warmrestart for system service

```

##### Enable WarmRestart

```
sonic(config)# warm-restart system enable
sonic(config)# warm-restart bgp enable
sonic(config)# warm-restart swss enable
sonic(config)# warm-restart teamd enable
```



##### Disable WarmRestart

```
sonic(config)# no warm-restart system enable
sonic(config)# no warm-restart bgp enable
sonic(config)# no warm-restart swss enable
sonic(config)# no warm-restart teamd enable
```



#### 3.6.2.1 Show Commands

```
sonic# show warm-restart
------------------------------------------------------
Module              Restore_count   State
------------------------------------------------------
aclsvcd             0
bgp                 0               disabled
dropmgrd            0
fdbsyncd            0               disabled
gearsyncd           0
ifamgrd             0
intfmgrd            0               disabled
iphelpermgr         0
l2mcmgrd            0
natsyncd            0
nbrmgrd             0
neighsyncd          0
orchagent           0               disabled
portmgrd            0
portsyncd           0
stpmgrd             0
syncd               0
teammgrd            0
teamsyncd           0
udldmgrd            0
vlanmgrd            0
vrfmgrd             0               disabled
vrrpmgrd            0
vrrpsyncd           0
vxlanmgrd           0
xcvrd               0



sonic# show running-configuration | grep warm
warm-restart bgp eoiu
warm-restart bgp enable
warm-restart bgp timer 1000
warm-restart swss enable
warm-restart swss timer 2000
warm-restart system enable
warm-restart teamd enable
warm-restart teamd timer 3000

```


#### 3.6.2.3 Debug Commands
N/A

#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support

| Command description                                          | Command Path                                                 |
| :----------------------------------------------------------- | ------------------------------------------------------------ |
| get warm restart restore_count  using sonic yang.   'module' can be set to any one of the following values: 'bgp', 'swss', 'teamd', 'system' | sonic-warmrestart:sonic-warmrestart/WARM_RESTART_TABLE/WARM_RESTART_TABLE_LIST={module}/restore_count |
| get warm restart using OC yang. restore_count                | openconfig-warmrestart:warmrestart/status/submodules/state/restore-count: |
| get warm restart state  using sonic yang.  'module' can be set to any one of the following values: 'bgp', 'swss', 'teamd', 'system' | sonic-warmrestart:warmrestart/WARM_RESTART_TABLE/WARM_RESTART_TABLE_LIST={module}/state |
| get warm restart state using OC yang.                        | openconfig-warmrestart:warmrestart/status/submodules/state/state: |
| Enable/Disable warm restart using sonic yang :   'module' can be set to any one of the following values: 'bgp', 'swss', 'teamd', 'system' | sonic-warmrestart:sonic-warmrestart/WARM_RESTART/WARM_RESTART_LIST={module}/enable |
| Enable/Disable warm restart using OC yang                    | openconfig-warmrestart:warmrestart/enable-warmrestart/modules={module}/config/enable |
| set/get bgp bgp_eoiu signal:    'module' can be set to any one of the following values: 'bgp' | sonic-warmrestart:sonic-warmrestart/WARM_RESTART/WARM_RESTART_LIST={module}/bgp_eoiu |
| set/get bgp timer using sonic yang :    'module' can be set to any one of the following values: 'bgp', | sonic-warmrestart:sonic-warmrestart/WARM_RESTART/WARM_RESTART_LIST={module}/bgp_timer |
| set/get module timer using OC yang: 'submodule' can be set to any one of the following values: 'bgp', 'swss', 'teamd', 'system' | openconfig-warmrestart:warmrestart/timers/timer={submodule}/config/value |
| set/get teamd timer :    'module' can be set to any one of the following values: bgp', 'swss', 'teamd', 'system' | sonic-warmrestart:sonic-warmrestart/WARM_RESTART/WARM_RESTART_LIST={module}/teamsyncd_timer |
| set/get swss timer :    'module' can be set to any one of the following values: 'swss' | sonic-warmrestart:sonic-warmrestart/WARM_RESTART/WARM_RESTART_LIST={module}/neighsyncd_timer |

# 4 Flow Diagrams

N/A

# 5 Error Handling
TBD

# 6 Serviceability and Debug
TBD

# 7 Warm Boot Support
N/A

# 8 Scalability
N/A

# 9 Unit Test
| Test Name                                | Test Description                                             |
| ---------------------------------------- | ------------------------------------------------------------ |
| Verify Warm-restart configuration        | CLI: Enable/disable WarmRestart for bgp, swss, teamd and system and check whether the db gets updated correctly in the config-db and state-db.  <br />CLI: Validate whether bgp_eiou value is configurable/readable only for bgp service and check whether the db gets updated correctly. <br />CLI: Validate whether timer value is configurable/readable for bgp,teamd,swss services and check whether db gets updated correctly. <br />CLI: Validate whether 'show running-configuration \| grep warm' command prints the configured data correctly. <br />CLI: Validate whether 'no warm-restart <service-name>' command removes warm-restart configuration of that service. |
| Verify REST/gNMI queries                 | REST/gNMI: Enable/disable WarmRestart for bgp, swss, teamd and system and check whether the db gets updated correctly.  <br />REST/gNMI: Validate whether bgp_eiou value is configurable/readable only for bgp service and check whether the db gets updated correctly <br />REST/gNMI: Validate whether timer value (bgp_timer, neighsyncd_timer, teamsyncd_timer) is configurable/readable for bgp,teamd,swss services and check whether db gets updated correctly. <br />REST/gNMI: Validate whether all db values of warm-restart tables are get/set correctly.  <br />REST: Check whether all rest APIs are returning expected value using curl. |
| Verify state-db and config-db table data | DB: Enable/Disable warm restart for different services and check whether the WARM_RESTART_ENABLE_TABLE in state-db gets updated correctly. <br />DB: Enable warm restart for different services and reboot the switch. Following reboot, check whether the WARM_RESTART_ENABLE_TABLE data in state-db is in sync with config-db data. |

# 10 Internal Design Information
TBD

