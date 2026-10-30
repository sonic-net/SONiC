# OpenConfig support for LLR(Link Layer Retry)

# High Level Design Document
#### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
    * [1.1 Requirements](#11-requirements)
      * [1.1.1 Functional Requirements](#111-functional-requirements)
      * [1.1.2 Configuration and Management Requirements](#112-configuration-and-management-requirements)
      * [1.1.3 Scalability Requirements](#113-scalability-requirements)
    * [1.2 Design Overview](#12-design-overview)
      * [1.2.1 Basic Approach](#121-basic-approach)      
  * [2 Functionality](#2-functionality)
      * [2.1 Target Deployment Use Cases](#21-target-deployment-use-cases)
  * [3 Design](#3-design)
    * [3.1 Overview](#31-overview)
    * [3.2 DB Changes](#32-db-changes)
      * [3.2.1 CONFIG DB](#321-config-db)      
      * [3.2.2 APP DB](#322-app-db)      
      * [3.2.3 STATE DB](#323-state-db)      
      * [3.2.4 ASIC DB](#324-asic-db)      
      * [3.2.5 COUNTER DB](#325-counter-db)      
    * [3.3 User Interface](#33-user-interface)
      * [3.3.1 Data Models](#331-data-models)
      * [3.3.2 REST API Support](#332-rest-api-support)
        * [3.3.2.1 GET](#3321-get)
        * [3.3.2.2 SET](#3322-set)
        * [3.3.2.3 DELETE](#3323-delete)
      * [3.3.3 gNMI Support](#333-gnmi-support)
        * [3.3.3.1 GET](#3331-get)
        * [3.3.3.2 SET](#3332-set)
        * [3.3.3.3 DELETE](#3333-delete)
        * [3.3.3.4 SUBSCRIBE](#3334-subscribe)
          * [3.3.3.4.1 ON_CHANGE](#33341-on_change)
          * [3.3.3.4.2 SAMPLE Subscriptions](#33342-sample-subscriptions)
          * [3.3.3.4.3 Target Defined Subscriptions](#33343-target-defined-subscriptions)
  * [4 Data Mapping](#4-data-mapping)
    * [4.1 OpenConfig to SONiC Mapping Table](#41-openconfig-to-sonic-mapping-table)
    * [4.2 Translation Notes](#42-translation-notes)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
    * [6.1 Functional Test Cases](#61-functional-test-cases)
    * [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)     
[Table 2: OpenConfig YANG SONiC YANG Mapping](#41-openconfig-to-sonic-mapping-table)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 04/17/2026  | Arthi G | Initial version                              |

# About this Manual
This document provides general information about the OpenConfig configuration of Link Layer Retry(LLR) in SONiC.

# Scope
- This document describes the high level design of configuration of Link Layer Retry using openconfig models via REST & gNMI. 
- This does not cover the SONiC yang model. For SONiC yang refer to https://docs.google.com/presentation/d/1WCemJGMyExsnbbvvxBLMN98KSfxaVGrDibItDLji9Bc/edit?usp=sharing) 
- This is new openconfig yang model added for Link Layer Retry feature.


<pre>
module: openconfig-llr
  +--rw llr
     +--rw config
     +--ro state
     +--rw interfaces
     |  +--rw interface* [name]
     |     +--rw name      -> ../config/name
     |     +--rw config
     |     |  +--rw name?          oc-if:interface-id
     |     |  +--rw llr-mode?      llr-mode-enumeration
     |     |  +--rw llr-local?     boolean
     |     |  +--rw llr-remote?    boolean
     |     |  +--rw llr-profile?   string
     |     +--ro state
     |        +--ro name?          oc-if:interface-id
     |        +--ro llr-mode?      llr-mode-enumeration
     |        +--ro llr-local?     boolean
     |        +--ro llr-remote?    boolean
     |        +--ro llr-profile?   string
     |        +--ro counters
     |           +--ro tx-init-ctl-os?             oc-yang:counter64
     |           +--ro tx-init-echo-ctl-os?        oc-yang:counter64
     |           +--ro tx-ack-ctl-os?              oc-yang:counter64
     |           +--ro tx-nack-ctl-os?             oc-yang:counter64
     |           +--ro tx-discard?                 oc-yang:counter64
     |           +--ro tx-ok?                      oc-yang:counter64
     |           +--ro tx-poisoned?                oc-yang:counter64
     |           +--ro tx-replay?                  oc-yang:counter64
     |           +--ro rx-init-ctl-os?             oc-yang:counter64
     |           +--ro rx-init-echo-ctl-os?        oc-yang:counter64
     |           +--ro rx-ack-ctl-os?              oc-yang:counter64
     |           +--ro rx-nack-ctl-os?             oc-yang:counter64
     |           +--ro rx-ack-nack-seq-error?      oc-yang:counter64
     |           +--ro rx-ok?                      oc-yang:counter64
     |           +--ro rx-poisoned?                oc-yang:counter64
     |           +--ro rx-bad?                     oc-yang:counter64
     |           +--ro rx-expected-seq-good?       oc-yang:counter64
     |           +--ro rx-expected-seq-poisoned?   oc-yang:counter64
     |           +--ro rx-expected-seq-bad?        oc-yang:counter64
     |           +--ro rx-missing-seq?             oc-yang:counter64
     |           +--ro rx-duplicate-seq?           oc-yang:counter64
     |           +--ro rx-replay?                  oc-yang:counter64
     +--rw profiles
        +--rw profile* [name]
           +--rw name      -> ../config/name
           +--rw config
           |  +--rw name?                     string
           |  +--rw max-outstanding-frames    uint32
           |  +--rw max-outstanding-bytes     uint32
           |  +--rw max-replay-count?         uint8
           |  +--rw max-replay-timer?         uint32
           |  +--rw pcs-lost-timeout?         uint32
           |  +--rw data-age-timeout?         uint32
           |  +--rw ctlos-spacing-bytes?      uint16
           |  +--rw init-action?              identityref
           |  +--rw flush-action?             identityref
           +--ro state
              +--ro name?                     string
              +--ro max-outstanding-frames    uint32
              +--ro max-outstanding-bytes     uint32
              +--ro max-replay-count?         uint8
              +--ro max-replay-timer?         uint32
              +--ro pcs-lost-timeout?         uint32
              +--ro data-age-timeout?         uint32
              +--ro ctlos-spacing-bytes?      uint16
              +--ro init-action?              identityref
              +--ro flush-action?             identityref
</pre>

# Definition/Abbreviation
### Table 1: Abbreviations

| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |


# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig Link Layer Retry YANG models.
2. Configuring LLR per-interface: mode, local/remote status, and profile associations.
3. Defining LLR Profiles: managing retransmission parameters like outstanding frames/bytes and timers.
4. Retrieving Operational State: monitoring active LLR settings and detailed error/performance counters.
5. Support configurations via REST and gNMI.

### 1.1.2 Configuration and Management Requirements
The Link Layer Retry (LLR) configuration/management can be done via REST and gNMI. The implementation will return an error if configuration is not allowed due to misconfiguration or un-supported node is accessed.

### 1.1.3 Scalability Requirements
NA

## 1.2 Design Overview
### 1.2.1 Basic Approach
This feature adds support for the Link Layer Retry mechanism, which ensures reliable frame delivery by managing local retransmission of lost frames due to link errors at the data link layer. There is already HLD for SONiC LLR yang. This feature adds Openconfig based Yang models for the Link Layer Retry feature.


# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can perform POST, PUT, PATCH, DELETE, GET operations on the supported YANG paths.
2. gNMI client with support for capabilities, get, set and subscribe based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20Framework.md]

## 3.2 DB Changes
### 3.2.1 CONFIG DB
There are no changes to CONFIG DB schema definition.  

### 3.2.2 APP DB
There are no changes to APP DB schema definition.

### 3.2.3 STATE DB
There are no changes to STATE DB schema definition.  

### 3.2.4 ASIC DB
There are no changes to ASIC DB schema definition.

### 3.2.5 COUNTER DB
There are no changes to COUNTER DB schema definition.

## 3.3 User Interface
### 3.3.1 Data Models

### 3.3.2 REST API Support
#### 3.3.2.1 GET

Sample GET for an LLR interface configuration:
```
curl -k -X GET "https://<ip:port>/restconf/data/openconfig-llr:llr/interfaces/interface=Ethernet0/config" -H "accept: application/yang-data+json"

{"openconfig-llr:config":{"name":"Ethernet0","llr-mode":"STATIC","llr-local":true,"llr-remote":true,"llr-profile":"llr_800000_40m_profile"}}
```

Sample GET for an LLR profile:
```
curl -k -X GET "https://<ip:port>/restconf/data/openconfig-llr:llr/profiles/profile=llr_800000_40m_profile" -H "accept: application/yang-data+json"

{"openconfig-llr:profile":[{"name":"llr_800000_40m_profile","config":{"name":"llr_800000_40m_profile","max-outstanding-frames":128,"max-outstanding-bytes":65536,"max-replay-count":1,"max-replay-timer":0,"pcs-lost-timeout":0,"data-age-timeout":0,"ctlos-spacing-bytes":2048,"init-action":"openconfig-llr-profile:BEST_EFFORT","flush-action":"openconfig-llr-profile:BEST_EFFORT"},"state":{"name":"llr_800000_40m_profile","max-outstanding-frames":128,"max-outstanding-bytes":65536,"max-replay-count":1,"max-replay-timer":0,"pcs-lost-timeout":0,"data-age-timeout":0,"ctlos-spacing-bytes":2048,"init-action":"openconfig-llr-profile:BEST_EFFORT","flush-action":"openconfig-llr-profile:BEST_EFFORT"}}]}
```

#### 3.3.2.2 SET

Sample PATCH to apply an LLR profile to an interface:
```
curl -k -X PATCH "https://<ip:port>/restconf/data/openconfig-llr:llr/interfaces/interface=Ethernet4/config/llr-profile" -H "Content-Type: application/yang-data+json" -d '{"openconfig-llr:llr-profile": "llr_800000_40m_profile"}'
```
Sample PUT to create a new LLR profile:
```
curl -k -X PUT "https://<ip:port>/restconf/data/openconfig-llr:llr/profiles/profile=llr_800000_40m_profile" -H "Content-Type: application/yang-data+json" -d '{"openconfig-llr:profile": [{"name": "llr_800000_40m_profile", "config": {"name": "llr_800000_40m_profile", "max-outstanding-frames": 256, "max-outstanding-bytes": 131072}}]}'
```

#### 3.3.2.3 DELETE
Sample DELETE for an LLR interface configuration (by deleting the profile association):
```
curl -k -X DELETE "https://<ip:port>/restconf/data/openconfig-llr:llr/interfaces/interface=Ethernet4/config/llr-profile"
```

Sample DELETE for an LLR profile:
```
curl -k -X DELETE "https://<ip:port>/restconf/data/openconfig-llr:llr/profiles/profile=llr_800000_40m_profile"
```

### 3.3.3 gNMI Support
#### 3.3.3.1 GET
Supported

LLR interface GET:
```
gnmi_get -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath /openconfig-llr:llr/interfaces/interface[name=Ethernet0]/config
```
Response:
```
== getResponse:
notification: <
  timestamp: 1748361000000000000
  prefix: <>
  update: <
    path: <
      elem: <
        name: "openconfig-llr:llr"
      >
      elem: <
        name: "interfaces"
      >
      elem: <
        name: "interface"
        key: <
          key: "name"
          value: "Ethernet0"
        >
      >
      elem: <
        name: "config"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-llr:config\":{\"name\":\"Ethernet0\",\"llr-mode\":\"STATIC\",\"llr-local\":true,\"llr-remote\":true,\"llr-profile\":\"llr_800000_40m_profile\"}}"
    >
  >
>
```

LLR profile GET:
```
gnmi_get -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath /openconfig-llr:llr/profiles/profile[name=llr_800000_40m_profile]/config
```
Response:
```
== getResponse:
notification: <
  timestamp: 1748361200000000000
  prefix: <>
  update: <
    path: <
      elem: <
        name: "openconfig-llr:llr"
      >
      elem: <
        name: "profiles"
      >
      elem: <
        name: "profile"
        key: <
          key: "name"
          value: "llr_800000_40m_profile"
        >
      >
      elem: <
        name: "config"
      >
    >
    val: <
      json_ietf_val: "{\"openconfig-llr:config\":{\"name\":\"llr_800000_40m_profile\",\"max-outstanding-frames\":128,\"max-outstanding-bytes\":65536,\"max-replay-count\":1,\"max-replay-timer\":0,\"pcs-lost-timeout\":0,\"data-age-timeout\":0,\"ctlos-spacing-bytes\":2048,\"init-action\":\"openconfig-llr-profile:BEST_EFFORT\",\"flush-action\":\"openconfig-llr-profile:BEST_EFFORT\"}}"
    >
  >
>
```

#### 3.3.3.2 SET
Supported

Sample SET to update an LLR interface configuration:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -update /openconfig-llr:llr/interfaces/interface[name=Ethernet0]/config:@/home/admin/llr_interface.json

llr_interface.json:
{
  "openconfig-llr:config": {
    "name": "Ethernet0",
    "llr-mode": "STATIC",
    "llr-local": true,
    "llr-remote": true,
    "llr-profile": "llr_800000_40m_profile"
  }
}
```

Sample SET to create a new LLR profile:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -update /openconfig-llr:llr/profiles/profile[name=nllr_800000_40m_profile]:@/home/admin/llr_profile.json

llr_profile.json:
{
  "openconfig-llr:config": {
    "name": "llr_800000_40m_profile",
    "max-outstanding-frames": 256,
    "max-outstanding-bytes": 131072
  }
}
```

#### 3.3.3.3 DELETE
Supported

Sample DELETE for an LLR profile:
```
gnmi_set -insecure -logtostderr -username USER -password PASSWORD -target_addr localhost:8080 -xpath_target OC-YANG -delete /openconfig-llr:llr/profiles/profile[name=llr_800000_40m_profile]
== setRequest:
prefix: <
  target: "OC-YANG"
>
delete: <
  path: <
    elem: <
      name: "openconfig-llr:llr"
    >
    elem: <
      name: "profiles"
    >
    elem: <
      name: "profile"
      key: <
        key: "name"
        value: "llr_800000_40m_profile"
      >
    >
  >
>

== setResponse:
prefix: <
  target: "OC-YANG"
>
response: <
  path: <
    elem: <
      name: "openconfig-llr:llr"
    >
    elem: <
      name: "profiles"
    >
    elem: <
      name: "profile"
      key: <
        key: "name"
        value: "llr_800000_40m_profile"
      >
    >
  >
  op: DELETE
>
```

#### 3.3.3.4 SUBSCRIBE
This section outlines the supported gNMI telemetry subscription types (ON_CHANGE, SAMPLE, and TARGET_DEFINED) using gnmi_cli targeted at the OpenConfig LLR paths.
##### 3.3.3.4.1 ON_CHANGE

LLR Interface Config (Config Level)
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-llr:llr/interfaces/interface[name=Ethernet0]/config --with_user_pass
```
Example Output:
```json
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet0": {
            "config": {
              "name": "Ethernet0",
              "llr-mode": "STATIC",
              "llr-local": true,
              "llr-profile": "llr_800000_40m_profile"
            }
          }
        }
      }
    }
  }
}
```
LLR Interface Config (Wildcard)
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-llr:llr/interfaces/interface[name=*]/config --with_user_pass
```
Example Output:
```json
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet0": {
            "config": {
              "llr-local": true,
              "llr-profile": "llr_800000_40m_profile"
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet1": {
            "config": {
              "llr-local": true,
              "llr-mode": "STATIC"
            }
          }
        }
      }
    }
  }
}
```
LLR Profile Config (Leaf)
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type ON_CHANGE -query /openconfig-llr:llr/profiles/profile[name=llr_800G_40m_profile]/config/max-outstanding-frames --with_user_pass
```
Example Output:
```json
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "profiles": {
        "profile": {
          "llr_800000_40m_profile": {
            "config": {
              "max-outstanding-frames": 100
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "profiles": {
        "profile": {
          "llr_800000_40m_profile": {
            "config": {
              "max-outstanding-frames": 150
            }
          }
        }
      }
    }
  }
}
```
##### 3.3.3.4.2 SAMPLE Subscriptions
LLR Interface Counters (State Level)
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-llr:llr/interfaces/interface[name=Ethernet0]/state/counters --with_user_pass
```
Example Output:
```json
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet0": {
            "state": {
              "counters": {
                "tx-ok": 104532,
                "rx-ok": 104500,
                "tx-replay": 12,
                "rx-missing-seq": 3
              }
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet0": {
            "state": {
              "counters": {
                "tx-ok": 104580,
                "rx-ok": 104545,
                "tx-replay": 12,
                "rx-missing-seq": 3
              }
            }
          }
        }
      }
    }
  }
}
```
LLR Profile Config (Config Level)
```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type streaming -streaming_type SAMPLE -query /openconfig-llr:llr/profiles/profile[name=llr_800G_40m_profile]/config --with_user_pass
```
Example Output:
```json
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "profiles": {
        "profile": {
          "llr_800000_40m_profile": {
            "config": {
              "max-outstanding-frames": 50,
              "max-outstanding-bytes": 150000,
              "pcs-lost-timeout": 1000,
              "data-age-timeout": 500
            }
          }
        }
      }
    }
  }
}
```
##### 3.3.3.4.3 Target Defined Subscriptions
LLR Combined Profile and Interface Subscription

```
gnmi_cli -insecure -logtostderr -target OC_YANG -address localhost:8080 -query_type s -query /openconfig-llr:llr/interfaces/interface[name=Ethernet0]/state/llr-mode,/openconfig-llr:llr/profiles/profile[name=llr_800000_40m_profile]/config --with_user_pass

{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "interfaces": {
        "interface": {
          "Ethernet0": {
            "state": {
              "llr-mode": "STATIC"
            }
          }
        }
      }
    }
  }
}
{
  "OC_YANG": {
    "openconfig-llr:llr": {
      "profiles": {
        "profile": {
          "llr_800000_40m_profile": {
            "config": {
              "max-outstanding-frames": 100,
              "max-outstanding-bytes": 500000,
              "max-replay-count": 5
            }
          }
        }
      }
    }
  }
}
```

# 4 Data Mapping

## 4.1 OpenConfig to SONiC Mapping Table

| OpenConfig YANG Node | SONiC YANG File | DB Name | Table:Field |
|----------------------------------------------------------------|-----------------|-----------|--------------------------------|
| **profiles/profile** | | | |
| config/name | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:name |
| config/max-outstanding-frames | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:max_outstanding_frames |
| config/max-outstanding-bytes | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:max_outstanding_bytes |
| config/max-replay-count | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:max_replay_count |
| config/max-replay-timer | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:max_replay_timer |
| config/pcs-lost-timeout | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:pcs_lost_timeout |
| config/data-age-timeout | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:data_age_timeout |
| config/ctlos-spacing-bytes | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:ctlos_spacing_bytes |
| config/init-action | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:init_action |
| config/flush-action | sonic-llr-profile.yang | CONFIG_DB | LLR_PROFILE:flush_action |
| **interfaces/interface** | | | |
| config/name | sonic-llr-port.yang | CONFIG_DB | PORT:name |
| config/llr-mode | sonic-llr-port.yang | CONFIG_DB | PORT:llr_mode |
| config/llr-local | sonic-llr-port.yang | CONFIG_DB | PORT:llr_mode |
| config/llr-remote | sonic-llr-port.yang | CONFIG_DB | PORT:llr_mode |
| config/llr-profile | sonic-llr-port.yang | CONFIG_DB | PORT:llr_profile |
| state/llr-local | - | STATE_DB | LLR_STAT_TABLE:llr_local |
| state/llr-remote | - | STATE_DB | LLR_STAT_TABLE:llr_remote |
| state/counters/* | - | COUNTERS_DB| PORT_TABLE |

**Notes:**

## 4.2 Translation Notes

Translation Notes:  
1. The `openconfig-llr` model maps to the `LLR_PROFILE` table in `CONFIG_DB` for profiles and to the `LLR_PORT` table in `CONFIG_DB` for interface-specific settings.
2. Operational state, including local/remote status is retrieved from `LLR_STAT_TABLE` in `STATE_DB` and `PORT_TABLE` in `COUNTERS_DB`.

# 5 Error Handling
Invalid configurations/operations will report an error.

# 6 Unit Test cases
## 6.1 Functional Test Cases
Operations:  
gNMI - (Create/Update/Delete/Replace/Get/Subscribe)  
REST - POST/PATCH/DELETE/PUT/GET  
1. Verify that LLR profiles can be created, updated, and deleted via REST and gNMI.
2. Verify that LLR can be enabled on an interface by setting the `llr-mode`, `llr-local`, `llr-remote` and `llr-profile`.
3. Verify that LLR can be disabled on an interface.
4. Verify that GET operations retrieve the correct configuration and state for LLR profiles and interfaces.
5. Verify that gNMI subscriptions (ON_CHANGE for config, SAMPLE for counters) work correctly for all relevant LLR paths.
6. Verify that all LLR counters can be retrieved and correctly reflect traffic and error conditions.

## 6.2 Negative Test Cases
1. Verify that applying a non-existent LLR profile to an interface returns an error.
2. Verify that creating an LLR profile with out-of-range parameter values returns an error.
3. Verify that attempting to configure a read-only state attribute (e.g., counters) returns an error.
4. Verify that GET on a non-existent LLR profile or interface returns an appropriate "not found" error.
5. Verify that deleting an LLR profile that is currently in use by an interface is handled correctly (e.g., rejected or with a warning).
