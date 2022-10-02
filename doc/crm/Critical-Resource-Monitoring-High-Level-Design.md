# Critical resource monitoring in SONiC
# High Level Design Document
### Rev 0.1

# Table of Contents
  * [List of Tables](#list-of-tables)

  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Definitions/Abbreviation](#definitionsabbreviation)
 
  * [1 Subsystem Requirements Overview](#1-subsystem-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
      * [1.1.1 Resources to be monitored](#111-resources-to-be-monitored)
	  * [1.1.2 Monitoring process requirements](#112-monitoring-process-requirements)
	* [1.2 CLI requirements](#12-cli-requirements)

  * [2 Modules Design](#2-modules-design)
    * [2.1 Config DB](#21-config-db)
      * [2.1.1 CRM Table](#211-crm-table)
    * [2.2 Counters DB](#22-counters-db)
      * [2.2.1 CRM_STATS Table](#221-crm_stats_table)
      * [2.2.2 CRM_ACL_GROUP_STATS](#222-crm_acl_group_stats)
    * [2.4 Orchestration Agent](#24-orchestration-agent)
    * [2.6 SAI](#26-sai)
	* [2.7 CLI](#27-cli)
	  * [2.7.1 CRM utility interface](#271-crm-utility-interface)
	    * [2.7.1.1 CRM utility config syntax](#2711-crm-utility-config-syntax)
		* [2.7.1.2 CRM utility show syntax](#2712-crm-utility-show-syntax)
      * [2.7.2 Config CLI command](#272-config_cli_command)
	  * [2.7.3 Show CLI command](#273-show_cli_command)

  * [3 Flows](#3-flows)
	* [3.1 CRM monitoring](#31-crm-monitoring)
	* [3.2 CRM CLI config](#32-crm-cli-config)
	* [3.3 CRM CLI show](#33-crm-cli-show)

  * [4 Open Questions](#4-open-questions)

# List of Tables
* [Table 1: Revision](#revision)
* [Table 2: Abbreviations](#definitionsabbreviation)
* [Table 3: CRM SAI attributes](#crn-sai-attributes)

###### Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Volodymyr Samotiy  | Initial version                   |

# About this Manual
This document provides general information about the Critical Resource Monitoring feature implementation in SONiC.
# Scope
This document describes the high level design of the Critical Resource Monitoring feature.
# Definitions/Abbreviation
###### Table 2: Abbreviations
| Definitions/Abbreviation | Description                                |
|--------------------------|--------------------------------------------|
| CRM                      | Critical Resource Monitoring               |
| API                      | Application Programmable Interface         |
| SAI                      | Swich Abstraction Interface                |
# 1 Subsystem Requirements Overview
## 1.1 Functional requirements
Detailed description of the Critical Resource Monitoring feature requirements is here: [CRM Requirements](https://github.com/sonic-net/SONiC/blob/gh-pages/doc/crm/CRM_requirements.md).

This section describes the SONiC requirements for Critical Resource Monitoring (CRM) feature. CRM should monitor utilization of  ASIC resources by polling SAI attributes.

At a high level the following should be supported:

- CRM should log a message if there are any resources that exceed defined threshold value.
- CLI commands to check current usage and availability of monitored resources.

### 1.1.1 Resources to be monitored
1. **IPv4 routes:** query currently used and available number of  entries
2. **IPv6 routes:** query currently used and available number of entries
3. **IPv4 Nexthops:** query currently used available number of entries
4. **IPv6 Nexthops:** query currently used and available number of entries
5. **IPv4 Neighbors:** query currently used and available number of entries
6. **IPv6 Neighbors:** query currently used and available number of entries
7. **Next-hop group member:** query currently used and available number of entries
8. **Next-hop group objects:** query currently used and available number of entries
9. **ACL:**  query currently used and available number of entries
	- ACL Table
	- ACL Group
	- ACL Entries
	- ACL Counters/Statistics
10. **FDB entries:** query currently used and available entries
## 1.2 Monitoring process requirements
Monitoring process should periodically poll SAI counters for all required resources, then it should  check whether retrieved values exceed defined thresholds and log appropriate SYSLOG message.

- User should be able to configure LOW and HIGH thresholds.
- User should be able to configure thresholds in the following formats:
	- percentage
	- actual used count
	- actual free count
- CRM feature should log "SYSLOG" message if there are any resources that exceed LOW or HIGH threshold.
- CRM should support two types of "SYSLOG" messages:
	- EXCEEDED for high threshold.
	- CLEAR for low threshold.
- "SYSLOG" messages should be in the following format:

```"<Date/Time> WARNING <Process name>: THRESHOLD_EXCEEDED for <TH_TYPE> <%> Used count <value> free count <value>"```

```"<Date/Time> WARNING <Process name>: THRESHOLD_CLEAR for <TH_TYPE> <%> Used count <value> free count <value>"```

```<TH_TYPE> = <TH_PERCENTAGE, TH_USED, TH_FREE>```

- Default polling interval should be set to 5 minutes.
- Default HIGH threshold should be set to 85%.
- Default LOW threshold should be set to 70%.
- CRM feature should suppress SYSLOG messages after printing for 10 times.
## 1.3 CLI requirements
- User should be able to query usage and availability of monitored resources.
- User should be able to configure thresholds values.

# 2 Modules Design
## 2.1 Config DB
### 2.1.1 CRM Table
New "CRM" table should be added to ConfigDB in order to store CRM related configuration: polling interval and LOW/HIGH threshold values.
```
; Defines schema for CRM configuration attributes
key                                        = CRM                               ; CRM configuration
; field                                    = value
polling_interval                           = 1*4DIGIT                          ; CRM polling interval
ipv4_route_threshold_type                  = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv4 route' resource
ipv6_route_threshold_type                  = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv6 route' resource
ipv4_nexthop_threshold_type                = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv4 next-hop' resource
ipv6_nexthop_threshold_type                = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv6 next-hop' resource
ipv4_neighbor_threshold_type               = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv4 neighbor' resource
ipv6_neighbor_threshold_type               = "percentage" / "used" / "free"    ; CRM threshold type for 'ipv6 neighbor' resource
nexthop_group_member_threshold_type        = "percentage" / "used" / "free"    ; CRM threshold type for 'next-hop group member' resource
nexthop_group_threshold_type               = "percentage" / "used" / "free"    ; CRM threshold type for 'next-hop group object' resource
acl_table_threshold_type                   = "percentage" / "used" / "free"    ; CRM threshold type for 'acl table' resource
acl_group_threshold_type                   = "percentage" / "used" / "free"    ; CRM threshold type for 'acl group' resource
acl_entry_threshold_type                   = "percentage" / "used" / "free"    ; CRM threshold type for 'acl entry' resource
acl_counter_threshold_type                 = "percentage" / "used" / "free"    ; CRM threshold type for 'acl counter' resource
fdb_entry_threshold_type                   = "percentage" / "used" / "free"    ; CRM threshold type for 'fdb entry' resource
ipv4_route_low_threshold                   = 1*4DIGIT                          ; CRM low threshold for 'ipv4 route' resource
ipv6_route_low_threshold                   = 1*4DIGIT                          ; CRM low threshold for 'ipv6 route' resource
ipv4_nexthop_low_threshold                 = 1*4DIGIT                          ; CRM low threshold for 'ipv4 next-hop' resource
ipv6_nexthop_low_threshold                 = 1*4DIGIT                          ; CRM low threshold for 'ipv6 next-hop' resource
ipv4_neighbor_low_threshold                = 1*4DIGIT                          ; CRM low threshold for 'ipv4 neighbor' resource
ipv6_neighbor_low_threshold                = 1*4DIGIT                          ; CRM low threshold for 'ipv6 neighbor' resource
nexthop_group_member_low_threshold         = 1*4DIGIT                          ; CRM low threshold for 'next-hop group member' resource
nexthop_group_low_threshold                = 1*4DIGIT                          ; CRM low threshold for 'next-hop group object' resource
acl_table_low_threshold                    = 1*4DIGIT                          ; CRM low threshold for 'acl table' resource
acl_group_low_threshold                    = 1*4DIGIT                          ; CRM low threshold for 'acl group' resource
acl_entry_low_threshold                    = 1*4DIGIT                          ; CRM low threshold for 'acl entry' resource
acl_counter_low_threshold                  = 1*4DIGIT                          ; CRM low threshold for 'acl counter' resource
fdb_entry_low_threshold                    = 1*4DIGIT                          ; CRM low threshold for 'fdb entry' resource
ipv4_route_high_threshold                  = 1*4DIGIT                          ; CRM high threshold for 'ipv4 route' resource
ipv6_route_high_threshold                  = 1*4DIGIT                          ; CRM high threshold for 'ipv6 route' resource
ipv4_nexthop_high_threshold                = 1*4DIGIT                          ; CRM high threshold for 'ipv4 next-hop' resource
ipv6_nexthop_high_threshold                = 1*4DIGIT                          ; CRM high threshold for 'ipv6 next-hop' resource
ipv4_neighbor_high_threshold               = 1*4DIGIT                          ; CRM high threshold for 'ipv4 neighbor' resource
ipv6_neighbor_high_threshold               = 1*4DIGIT                          ; CRM high threshold for 'ipv6 neighbor' resource
nexthop_group_member_high_threshold        = 1*4DIGIT                          ; CRM high threshold for 'next-hop group member' resource
nexthop_group_high_threshold               = 1*4DIGIT                          ; CRM high threshold for 'next-hop group object' resource
acl_table_high_threshold                   = 1*4DIGIT                          ; CRM high threshold for 'acl table' resource
acl_group_high_threshold                   = 1*4DIGIT                          ; CRM high threshold for 'acl group' resource
acl_entry_high_threshold                   = 1*4DIGIT                          ; CRM high threshold for 'acl entry' resource
acl_counter_high_threshold                 = 1*4DIGIT                          ; CRM high threshold for 'acl counter' resource
fdb_entry_high_threshold                   = 1*4DIGIT                          ; CRM high threshold for 'fdb entry' resource
```
## 2.2 Counters DB
Two new tables should be added to the CountersDB in order to represent currently used and available entries for the CRM resources.
### 2.2.1 CRM_STATS Table
This table should store all global CRM stats.
```
; Defines schema for CRM counters attributes
key                                         = CRM_STATS       ; CRM stats entry
; field                                     = value
CRM_STATS_IPV4_ROUTE_AVAILABLE              = 1*20DIGIT       ; number of available entries for 'ipv4 route' resource
CRM_STATS_IPV6_ROUTE_AVAILABLE              = 1*20DIGIT       ; number of available entries for 'ipv6 route' resource
CRM_STATS_IPV4_NEXTHOP_AVAILABLE            = 1*20DIGIT       ; number of available entries for 'ipv4 next-hop' resource
CRM_STATS_IPV6_NEXTHOP_AVAILABLE            = 1*20DIGIT       ; number of available entries for 'ipv6 next-hop' resource
CRM_STATS_IPV4_NEIGHBOR_AVAILABLE           = 1*20DIGIT       ; number of available entries for 'ipv4 neighbor' resource
CRM_STATS_IPV6_NEIGHBOR_AVAILABLE           = 1*20DIGIT       ; number of available entries for 'ipv6 neighbor' resource
CRM_STATS_NEXTHOP_GROUP_MEMBER_AVAILABLE    = 1*20DIGIT       ; number of available entries for 'next-hop group member' resource
CRM_STATS_NEXTHOP_GROUP_OBJECT_AVAILABLE    = 1*20DIGIT       ; number of available entries for 'next-hop group object' resource
CRM_STATS_ACL_TABLE_AVAILABLE               = 1*20DIGIT       ; number of available entries for 'acl table' resource
CRM_STATS_ACL_GROUP_AVAILABLE               = 1*20DIGIT       ; number of available entries for 'acl group' resource
CRM_STATS_FDB_ENTRY_AVAILABLE               = 1*20DIGIT       ; number of available entries for 'fdb entry' resource
CRM_STATS_IPV4_ROUTE_USED                   = 1*20DIGIT       ; number of available entries for 'ipv4 route' resource
CRM_STATS_IPV6_ROUTE_USED                   = 1*20DIGIT       ; number of used entries for 'ipv6 route' resource
CRM_STATS_IPV4_NEXTHOP_USED                 = 1*20DIGIT       ; number of used entries for 'ipv4 next-hop' resource
CRM_STATS_IPV6_NEXTHOP_USED                 = 1*20DIGIT       ; number of used  entries for 'ipv6 next-hop' resource
CRM_STATS_IPV4_NEIGHBOR_USED                = 1*20DIGIT       ; number of available entries for 'ipv4 neighbor' resource
CRM_STATS_IPV6_NEIGHBOR_USED                = 1*20DIGIT       ; number of available entries for 'ipv6 neighbor' resource
CRM_STATS_NEXTHOP_GROUP_MEMBER_USED         = 1*20DIGIT       ; number of used entries for 'next-hop group member' resource
CRM_STATS_NEXTHOP_GROUP_OBJECT_USED         = 1*20DIGIT       ; number of used entries for 'next-hop group object' resource
CRM_STATS_ACL_TABLE_USED                    = 1*20DIGIT       ; number of used entries for 'acl table' resource
CRM_STATS_ACL_GROUP_USED                    = 1*20DIGIT       ; number of used entries for 'acl group' resource
CRM_STATS_FDB_ENTRY_USED                    = 1*20DIGIT       ; number of used entries for 'fdb entry' resource
```
### 2.2.2 CRM_ACL_GROUP_STATS
This table should store all "per ACL group" CRM stats .
```
; Defines schema for CRM counters attributes
key                                = CRM_ACL_GROUP_STATS:OID    ; CRM ACL group stats entry
; field                            = value
CRM_STATS_ACL_ENTRY_AVAILABLE      = 1*20DIGIT                  ; number of available entries for 'acl entry' resource
CRM_STATS_ACL_COUNTER_AVAILABLE    = 1*20DIGIT                  ; number of available entries for 'acl counter' resource
CRM_STATS_ACL_ENTRY_USED           = 1*20DIGIT                  ; number of used entries for 'acl entry' resource
CRM_STATS_ACL_COUNTER_USED         = 1*20DIGIT                  ; number of used entries for 'acl counter' resource
```
## 2.4 Orchestration Agent
New "CrmOrch" class should be implemented and it should run new CRM thread for all monitoring logic.

CRM thread should check whether some threshold is exceeded and log appropriate (CLEAR/EXCEEDED) SYSLOG message. Also number of already logged EXCEEDED messages should be tracked and once it reached the pre-defined value all CRM SYSLOG messages should be suppressed. When CLEAR message is logged then counter for number of logged messages should be cleared.

CLI show command should be able to display currently USED and AVAILABLE number of entries, but SAI provides API to query the current AVAILABLE  entries. So, OrchAgent (appropriate agent for each resource) should track respective entries that are programmed and update appropriate counter in "CrmOrch" cache. Also, "CrmOrch" should provide public API in order to allow other agents update local cache and then CRM thread  should periodically update CountersDB from the cache.
## 2.6 SAI
Shown below table represents all the SAI attributes which should be used to get required CRM counters.
###### Table 3: CRM SAI attributes
| CRM resource             | SAI attribute                                         |
|--------------------------|-------------------------------------------------------|
| IPv4 routes              | SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY            |
| IPv6 routes              | SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY            |
| IPv4 next-hops           | SAI_SWITCH_ATTR_AVAILABLE_IPV4_NEXTHOP_ENTRY          |
| IPv6 next-hops           | SAI_SWITCH_ATTR_AVAILABLE_IPV6_NEXTHOP_ENTRY          |
| IPv4 neighbors           | SAI_SWITCH_ATTR_AVAILABLE_IPV4_NEIGHBOR_ENTRY         |
| IPv6 neighbors           | SAI_SWITCH_ATTR_AVAILABLE_IPV6_NEIGHBOR_ENTRY         |
| Next-hop group members   | SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_MEMBER_ENTRY |
| Next-hop group objects   | SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_ENTRY        |
| ACL tables               | SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE                   |
| ACL groups               | SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE_GROUP             |
| ACL entries              | SAI_ACL_TABLE_ATTR_AVAILABLE_ACL_ENTRY                |
| ACL counters             | SAI_ACL_TABLE_ATTR_AVAILABLE_ACL_COUNTER              |
| FDB entries              | SAI_SWITCH_ATTR_AVAILABLE_FDB_ENTRY                   |
## 2.7 CLI
New CRM utility script should be implement in "sonic-utilities" in order to configure and display all CRM related information.
### 2.7.1 CRM utility interface
```
crm
Usage: crm [OPTIONS] COMMAND [ARGS]...

  Utility to operate with CRM configuration and resources.

Options:
  --help  Show this message and exit.

Commands:
  config   Set CRM configuration.
  show     Show CRM information.
```
#### 2.7.1.1 CRM utility config syntax
* ```polling interval <value>```
* ```thresholds all type [percentage|used|count]```
* ```thresholds all [low|high] <value>```
* ```thresholds [ipv4|ipv6] route type [percentage|used|count]```
* ```thresholds [ipv4|ipv6] route [low|high] <value>```
* ```thresholds [ipv4|ipv6] neighbor type [percentage|used|count]```
* ```thresholds [ipv4|ipv6] neighbor [low|high] <value>```
* ```thresholds [ipv4|ipv6] nexthop type [percentage|used|count]```
* ```thresholds [ipv4|ipv6] nexthop [low|high] <value>```
* ```thresholds nexthop group [member|object] type [percentage|used|count]```
* ```thresholds nexthop group [member|object] [low|high] <value>```
* ```thresholds acl [table|group] type [percentage|used|count]```
* ```thresholds acl [table|group] [low|high] <value>```
* ```thresholds acl group [entry|counter] type [percentage|used|count]```
* ```thresholds acl group [entry|counter] [low|high] <value>```
* ```thresholds fdb type [percentage|used|count]```
* ```thresholds fdb [low|high] <value>```
#### 2.7.1.2 CRM utility show syntax
* ```summary```
* ```[resources|thresholds] all```
* ```[resources|thresholds] [ipv4|ipv6] [route|neighbor|nexthop]```
* ```[resources|thresholds] nexthop group [member|object]```
* ```[resources|thresholds] acl [table|group]```
* ```[resources|thresholds] acl group [entry|counter]```
* ```[resources|thresholds] fdb```
### 2.7.2 Config CLI command
Config command should be extended in order to add "crm" alias to the CRM utility.
```
Usage: config [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'config' command

Options:
  --help  Show this message and exit.

Commands:
...
  crm               CRM related configuration.
```
### 2.7.3 Show CLI command
Show command should be extended in order to add "crm" alias to the CRM utility.
```
show
Usage: show [OPTIONS] COMMAND [ARGS]...

  SONiC command line - 'show' command

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  ...
  crm                   Show CRM related information
```
# 3 Flows
## 3.1 CRM monitoring
![](https://github.com/sonic-net/SONiC/blob/gh-pages/images/crm_hld/crm_monitoring_flow.png)
## 3.2 CRM CLI config
![](https://github.com/sonic-net/SONiC/blob/gh-pages/images/crm_hld/crm_cli_config_flow.png)
## 3.3 CRM CLI show
![](https://github.com/sonic-net/SONiC/blob/gh-pages/images/crm_hld/crm_cli_show_flow.png)
# 4 Open Questions
