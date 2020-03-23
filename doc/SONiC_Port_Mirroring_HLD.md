# SONiC Port Mirroring HLD
#### Rev 1.0

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1. Requirements Overview](#1-requirement-overview)
      * [1.1 Functional Requirements](#11-functional-requirements)
      * [1.2 Configuration and Management Requirements](#12-configuration-and-management-requirements)
      * [1.3 Scalability Requirements](#13-scalability-requirements)
      * [1.4 Warm Boot Requirements](#14-warm-boot-requirements)
  * [2. Functionality](#2-functionality)
      * [2.1 Functional Description](#21-functional-description)
  * [3. Design](#3-design)
      * [3.1 Overview](#31-overview)
      * [3.2 DB Changes](#32-db-changes)
          * [3.2.1 CONFIG DB](#321-config-db)
          * [3.2.2 APP_DB](#322-app_db)
          * [3.2.3 STATE_DB](#323-state_db)
          * [3.2.4 ASIC_DB](#324-asic_db)
          * [3.2.5 COUNTER_DB](#325-counter_db)
      * [3.3 Switch State Service Design](#33-switch-state-service-design)
          * [3.3.1 Orchestration Agent](#331-orchestration-agent)
          * [3.3.2 Other Process](#332-other-process)
      * [3.4 SAI](#35-sai)
      * [3.5 CLI](#36-cli)
          * [3.5.1 Data Models](#351-data-models)
          * [3.5.2 Configuration Commands](#352-configuration-commands)
          * [3.5.3 Show Commands](#353-show-commands)
          * [3.5.4 Clear Commands](#354-clear-commands)
          * [3.5.5 Debug Commands](#355-debug-commands)
          * [3.5.6 Rest API Support](#356-rest-api-support)
          * [3.5.7 GNMI Support](#357-gnmi-support)
  * [4. Flow Diagrams](#4-flow-diagrams)
  * [5. Error Handling](#5-Error-Handling)
  * [6. Serviceability and Debug](#6-serviceability-and-debug)
  * [7. Warm Boot Support](#7-warm-boot-support)
  * [8. Scalability](#8-scalability)
  * [9. Unit Test](#9-unit-test)

# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)


# Revision
| Rev |     Date    |       Author       | Change Description                         |
|:---:|:-----------:|:------------------:|--------------------------------------------|
| 0.1 | 05/17/2019  |   Rupesh Kumar      | Initial version                            |


# About this Manual
This document provides general information about extending mirroring implementation in SONiC.
# Scope
This document describes the high level design of Mirroring Enhancements feature. 


# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
|   SPAN                   |  Switched Port ANalyzer                |
|   ERSPAN                 |  Encapsulated Remote Switched Port ANalyzer                |


# 1 Requirement Overview
## 1.1 Functional Requirements

1. Port/Port-channel mirroring support
     - Add support to mirror ingress traffic on port/port-channel to SPAN/ERPSAN mirror session.
     - Add support to mirror egress traffic on port/port-channel to SPAN/ERSPAN mirror session.
     - Add support to mirror both ingress/egress traffic on port/port-channel to SPAN/ERSPAN mirror session.

2. Dynamic session management
    - Allow multiple source to single destination.
    - Each session supports mirroring from single port to single destination port.
    - Session-id created in SAI per destination port will be used when the same destination port is configured in other session.
      This effectively utilizes the hardware resource to be shared across multiple sessions.
    - Mirror session on source portchannel will be active if at least one port is part of portchannel.
    - Mirror session on source portchannel will become inactive when portchannel has no members.
    - ERSPAN session will be active/inactive based on destination IP reachability.

3. ACL rules can continue to use port/ERSPAN sessions as the action.

4. Configuration CLI for mirror session
    - CLI allows all flavors of mirror sessions.
    - CLI validation for all mandatory parameters in ERSPAN configuration.
    - CLI validation for all mandatory parameters in port/portchannel mirroring.
    - CLI to allow mirror session configuration only with destination port.


## 1.2 Configuration and Management Requirements
- Existing CLI 'config mirror_session add/remove'to be extended to include source port/portchannel.
- Existing CLI 'config mirror_session add/remove' to be extended to include destination port/portchannel.
- Existing CLI 'show mirror session' is extended to support all flavors of mirror sessions.


## 1.3 Scalability Requirements
- Up to max ASIC capable mirror sessions to be supported.
- Once max mirror sessions are created and user attempts to create new session, error will be logged in syslog.


## 1.4 Warm Boot Requirements
- Mirroring functionality should continue to work across warm reboot.

To support planned system warm boot.
To support SWSS docker warm boot.


# 2 Functionality

Refer section 1

## 2.2 Functional Description
Refer section 1.1

## 2.3 Functional Description

Mirroring to destination VLAN (RSPAN) is not supported in this release.

# 3 Design
## 3.1 Overview


## 3.2 DB Changes
### 3.2.1 CONFIG DB

Existing table PORT_MIRROR_TABLE is enhanced to accept new source and destination configuration options  in the configuration database. This table is filled by the management framework.

#### CONFIG_PORT_MIRROR_TABLE

    ;Configure SPAN/ERSPAN mirror session.
    ;storm control type - broadcast / unknown-unicast / unknown-multicast
    key       = PORT_MIRROR_TABLE:mirror_session_name ; mirror_session_name is
                                                      ; unique session
                                                      ; identifier
    ;field  = value
    destination_port = PORT_TABLE:ifname    ; ifname must be unique across PORT TABLE.
    source_port = PORT_TABLE:ifname    ; ifname must be unique across PORT,INTF,LAG TABLES
    direction     = ingress or egress or both           ; Direction ingress or egress or both.

    mirror_session_name = 1*255VCHAR

### 3.2.2 APP_DB
No tables are introduced in APP_DB
### 3.2.3 STATE_DB
No tables are introduced in STATE_DB.·

### 3.2.4 ASIC_DB
No changes are introduced in ASIC_DB.·
### 3.2.5 COUNTER_DB
No changes are introduced in COUNTER_DB.·

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent

Mirror Orchestration agent is modified to support this feature:
   - Handle both SPAN and ERSPAN sessions separately·
   - No changes to ERSPAN functionality.
   - Configure mirror session based on CONFIG_DB parameters.
   - Port mirror session is activated 
   - Populates the mirror attribute SAI structures and pushes the entry to ASIC_DB.·

## 3.4 SAI
Mirror SAI interface APIs are already defined. More details about SAI API and attributes are described below SAI Spec @

https://github.com/opencomputeproject/SAI/blob/master/inc/saimirror.h

## 3.5 CLI
### 3.5.1 Data Models
Custom Yang model will be introduced for this feature.

### 3.5.2 Configuration Commands

Existing mirror session commands are enhanced to support this feature.

    # Modify existing ERSPAN configuration as below.
    config mirror_session add erspan <session-name> <src_ip> <dst_ip> <gre> <dscp>  [ttl] [queue]

    #Configure Destination only span mirror session.
    config mirror_session add span <session-name> <destination_ifName>

    # Modify existing ERSPAN configuration to accept source port and direction
    config mirror_session add erspan <session-name> <src_ip> <dst_ip> <gre> <dscp>  [ttl] [queue] [src_port] [rx/tx/both]

    #Configure Port mirror span mirror session.
    config mirror_session add span <session-name> <destination_ifName> <source_ifName> <rx/tx/both>


KLISH CLI Support.

    # SPAN config
    # **switch(config)# [no] mirror-session <session-name>** <br>
    **switch(config-mirror-<session-name>)# [no] destination <dest_ifName> [source <src_ifName> direction <rx/tx/both>]** <br>
    dest_ifName can be port only
    src_ifName can be port/port-channel>

    # ERSPAN config
    **switch(config)# [no] mirror-session <session-name>** <br>
    **switch(config-mirror-<session-name>)# [no] destination erspan src_ip <src_ip> dst_ip <dst_ip> dscp < dscp > ttl < ttl > [ gre < gre >] [queue <queue>] [source <src_ifName> direction <rx/tx>**] <br>

### 3.5.3 Show Commands

The following show command display all the mirror sessions that are configured.

    # show mirror-session
    ERSPAN Sessions
    ---------------------------------------------------------------------------------------------------------
      Name     Status      SRC IP    DST IP    GRE   DSCP    TTL  Queue Policer      SRC Port    Direction
    everflow0  active    10.1.0.32  10.0.0.7    10    10      10
    everflow1  active    10.1.0.33  10.0.0.8    10    10      10                     Ethernet4    both

    SPAN Sessions
    ---------------------------------------------------------------------------------------------------------
      Name Status         DST Port         SRC Port Direction
     sess1 active        Ethernet4        Ethernet0     rx

KLISH show mirror-session is same as above.

###  3.5.4 Clear Commands
No command variants of config commands take care of clear config.

### 3.5.5 Debug Commands
Not applicable

### 3.5.6 REST API Support

- Please check all REST API from link @ https://<switch_ip>/ui link. 
- This webserver provides user information about all the REST URLS, REST Data. Return codes. 
- This webserver also provides interactive support to try REST queries.

- Following REST SET and GET APIs will be supported

The following show command display all the mirror sessions that are configured.

    # Get all mirror sessions
    # curl -X GET "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json"

    # Create SPAN session
    # curl -X POST "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json" -H "Content-Type: application/yang-data+json" -d "{ \"sonic-mirror-session:MIRROR_SESSION\": { \"MIRROR_SESSION_LIST\": [ { \"name\": \"sess1\", \"dst_port\": \"Ethernet10\", \"src_port\": \"Ethernet8\", \"direction\": \"rx\" } ] }}"

    # Delete all mirror sessions
    # curl -X DELETE "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json"

    # Delete specific mirror session
    # curl -X DELETE "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session/MIRROR_SESSION/MIRROR_SESSION_LIST=mirr3" -H "accept: application/yang-data+json"

### 3.5.7 GNMI Support


- Following GNMI set and get commands will be supported

    # Get all mirror sessions
    # gnmi_get -xpath /sonic-mirror-session:sonic-mirror-session -target_addr 127.0.0.1:8080 -insecure

    # Create SPAN session. mirror.json includes json payload same as rest-api above.
    # gnmi_set -update /sonic-mirror-session:sonic-mirror-session/:@./mirror.json -target_addr 127.0.0.1:8080 -insecure

    # Delete all mirror sessions
    # gnmi_set -delete /sonic-mirror-session:sonic-mirror-session -target_addr 127.0.0.1:8080 -insecure

    # Delete specific mirror session
    # gnmi_set -delete /sonic-mirror-session:sonic-mirror-session/MIRROR_SESSION/MIRROR_SESSION_LIST[name=Mirror1] -target_addr 127.0.0.1:8080 -insecure

# 4 Flow Diagrams

# 5 Error Handling

- show mirror session command will display any errors during session configuration and current status of session.
- Internal processing errors within SwSS will be logged in syslog with ERROR level
- SAI interaction errors will be logged in syslog

# 6 Serviceability and Debug

# 7 Warm Boot Support
The mirroring configurations be retained across warmboot so that source traffic gets mirrored properly to destination port.

# 8 Scalability

Max mirror sessions supported are silicon specific. Testing would be done by creating max mirror sessions on the switch.·
###### Table 3: Scaling limits
|Name                      |   Scaling value    |
|--------------------------|--------------------|
| Max mirror sessions      | silicon specific   |

# 9 Unit Test

## 9.1 CLI Test Cases

    1. Configure ERSPAN mirror session and verify all parameters are updated properly in CONFIG_DB 
    2. Configure SPAN mirror session and verify all parameters are updated properly in CONFIG_DB.
    3. Unconfigure ERSPAN/SPAN mirror sessions and check that it is updated in CONFIG_DB.
    4. Execute the show mirror session command to check the mirroring configuration.·
    5. Verify that the mirror configurations are correctly re-applied after cold reboot.
    6. Verify mirror session goes to in-active state when source port-channel has no members.
    7. Verify mirror session goes to active state when source port-channel has atleast one active member.

## 9.2 Rest API Test Cases
    8. Verify SPAN/ERSPAN mirroring can be configured via REST.
    9. Verify SPAN/ERSPAN mirroring can be un-configured via REST.

## 9.3 Functional Test Cases
    10. Verify that traffic on source port gets mirrored to destination port.
    11. Verify that traffic on source port-channel gets mirrored to destination port.
    12. Verify that traffic on source port/port-channel gets mirrored properly with proper Erspan session.
    13. Verify all existing test-cases of ERSPAN works properly.

## 9.4 Scaling Test Cases
    14. Configure max mirror sessions and verify that all are working properly.

## 9.5 Warm Boot Test Cases
    15. Verify that mirroring configurations are restored after warm boot.·
    16. Verify that mirroring continues to work across warm boot.

## 9.6 Negative Test Cases
    17. Verify that mirror configuration throws error with invalid interface or direction.
    18. Verify that mirror configuration throws error with already configured session.
