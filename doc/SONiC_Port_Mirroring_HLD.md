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
    key       = PORT_MIRROR:mirror_session_name ; mirror_session_name is
                                                      ; unique session
                                                      ; identifier
    ;field  = value
    type = SPAN or ERSPAN ; SPAN or ERSPAN session.
    destination_port = PORT_TABLE:ifname    ; ifname must be unique across PORT TABLE.
    source_port = PORT_TABLE:ifname    ; ifname must be unique across PORT,LAG TABLES
    direction     = RX or TX or BOTH           ; Direction RX or TX or BOTH.

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
   - Port mirror session will be active in below cases.
        - Session with destination port only config becomes active when session is created in SAI. These sessions can be used for ACL mirroring.
        - Session with source/destination/direction config will be active once the session created from SAI is programmed on the source ports.
   - Populates the mirror attribute SAI structures and pushes the entry to ASIC_DB.·

## 3.4 SAI
Mirror SAI interface APIs are already defined. 
More details about SAI API and attributes are described below SAI Spec @

https://github.com/opencomputeproject/SAI/blob/master/inc/saimirror.h
```
    /**
     * @brief SAI type of mirroring
     */
    typedef enum _sai_mirror_session_type_t
    {
        /** Local SPAN */
        SAI_MIRROR_SESSION_TYPE_LOCAL = 0,

        /** Remote SPAN */
        SAI_MIRROR_SESSION_TYPE_REMOTE,

        /** Enhanced Remote SPAN */
        SAI_MIRROR_SESSION_TYPE_ENHANCED_REMOTE,
    } sai_mirror_session_type_t;

    /**
     * @brief Destination/Analyzer/Monitor Port.
     *
     * @type sai_object_id_t
     * @flags MANDATORY_ON_CREATE | CREATE_AND_SET
     * @objects SAI_OBJECT_TYPE_PORT, SAI_OBJECT_TYPE_LAG
     * @condition SAI_MIRROR_SESSION_ATTR_MONITOR_PORTLIST_VALID == false
     */
    SAI_MIRROR_SESSION_ATTR_MONITOR_PORT,
```
https://github.com/opencomputeproject/SAI/blob/master/inc/saimirror.h

```
    /**
     * @brief Enable/Disable Mirror session
     *
     * Enable ingress mirroring by assigning list of mirror session object id
     * as attribute value, disable ingress mirroring by assigning object_count
     * as 0 in objlist.
     *
     * @type sai_object_list_t
     * @flags CREATE_AND_SET
     * @objects SAI_OBJECT_TYPE_MIRROR_SESSION
     * @default empty
     */
    SAI_PORT_ATTR_INGRESS_MIRROR_SESSION,

    /**
     * @brief Enable/Disable Mirror session
     *
     * Enable egress mirroring by assigning list of mirror session object id as
     * attribute value Disable egress mirroring by assigning object_count as 0
     * in objlist.
     *
     * @type sai_object_list_t
     * @flags CREATE_AND_SET
     * @objects SAI_OBJECT_TYPE_MIRROR_SESSION
     * @default empty
     */
    SAI_PORT_ATTR_EGRESS_MIRROR_SESSION,
```

## 3.5 CLI
### 3.5.1 Data Models
SONiC Yang model  and OpenConfig extension models will be introduced for this feature.

## openconfig-mirror-ext
```diff
  +--rw mirror
     +--rw config
     +--ro state
     +--rw sessions
        +--rw session* [name]
           +--rw name      -> ../config/name
           +--rw config
           |  +--rw name?        string
           |  +--rw dst-port?    oc-if:base-interface-ref
           |  +--rw src-port?    oc-if:base-interface-ref
           |  +--rw direction?   mirror-session-direction
           |  +--rw src-ip?      oc-inet:ip-address
           |  +--rw dst-ip?      oc-inet:ip-address
           |  +--rw dscp?        uint8
           |  +--rw gre-type?    string
           |  +--rw ttl?         uint8
           |  +--rw queue?       uint8
           +--ro state
              +--ro name?           string
              +--ro dst-port?       oc-if:base-interface-ref
              +--ro src-port?       oc-if:base-interface-ref
              +--ro direction?      mirror-session-direction
              +--ro src-ip?         oc-inet:ip-address
              +--ro dst-ip?         oc-inet:ip-address
              +--ro dscp?           uint8
              +--ro gre-type?       string
              +--ro ttl?            uint8
              +--ro queue?          uint8
              +--ro status?         string
              +--ro monitor-port?   oc-if:base-interface-ref
              +--ro dst-mac?        oc-yang:mac-address
              +--ro route-prefix?   oc-inet:ip-address
              +--ro vlan-id?        uint16
              +--ro next-hop-ip?    oc-inet:ip-address

```
| Prefix |     Module Name    |
|:---:|:-----------:|
| oc-mirror-ext | openconfig-mirror-ext  |
| oc-ext | openconfig-extensions  |
| oc-yang | openconfig-yang-types  |
| oc-inet | openconfig-inet-types  |
| oc-if | openconfig-interfaces  |

## sonic-mirror-session
```diff
  +--rw sonic-mirror-session
     +--rw MIRROR_SESSION
     |  +--rw MIRROR_SESSION_LIST* [name]
     |     +--rw name         string
     |     +--rw src_ip?      inet:ipv4-address
     |     +--rw dst_ip?      inet:ipv4-address
     |     +--rw gre_type?    string
     |     +--rw dscp?        uint8
     |     +--rw ttl?         uint8
     |     +--rw queue?       uint8
     |     +--rw dst_port?    union
     |     +--rw src_port?    union
     |     +--rw direction?   enumeration
     +--ro MIRROR_SESSION_TABLE
        +--ro MIRROR_SESSION_TABLE_LIST* [name]
           +--ro name            string
           +--ro status?         string
           +--ro monitor_port?   -> /prt:sonic-port/PORT/PORT_LIST/ifname
           +--ro dst_mac?        yang:mac-address
           +--ro route_prefix?   inet:ipv4-address
           +--ro vlan_id?        -> /svlan:sonic-vlan/VLAN/VLAN_LIST/name
           +--ro next_hop_ip?    inet:ipv4-address

```

### 3.5.2 Configuration Commands

Existing mirror session commands are enhanced to support this feature.
```
    # Modify existing ERSPAN configuration as below.
    config mirror_session add erspan <session-name> <src_ip> <dst_ip> <gre> <dscp>  [ttl] [queue] --policer <policer>

    #Configure Destination only span mirror session.
    config mirror_session add span <session-name> <destination_ifName>

    # Modify existing ERSPAN configuration to accept source port and direction
    config mirror_session add erspan <session-name> <src_ip> <dst_ip> <gre> <dscp>  [ttl] [queue] [src_port] [rx/tx/both] --policer <policer>

    #Configure Port mirror span mirror session.
    config mirror_session add span <session-name> <destination_ifName> <source_ifName> <rx/tx/both> [queue] --policer <policer>
```

KLISH CLI Support.

    # SPAN config
    # **switch(config)# [no] mirror-session <session-name>** <br>
    **switch(config-mirror-<session-name>)# [no] destination <dest_ifName> [source <src_ifName> direction <rx/tx/both>]** <br>
    dest_ifName can be port only
    src_ifName can be port/port-channel>

    # ERSPAN config
    **switch(config)# [no] mirror-session <session-name>** <br>
    **switch(config-mirror-<session-name>)# [no] destination erspan src_ip <src_ip> dst_ip <dst_ip> dscp < dscp > ttl < ttl > [ gre < gre >] [queue <queue>] [source <src_ifName> direction <rx/tx>**] [policer <policer>]<br>

### 3.5.3 Show Commands

The following show command display all the mirror sessions that are configured.

    # show mirror-session
    ERSPAN Sessions
    Name       Status   SRC IP    DST IP      GRE    DSCP    TTL  Queue    Policer    Monitor Port    SRC Port    Direction
    ---------  ------   --------  --------  -----  ------  -----  -------  ---------  --------------  ----------  -----------
    everflow0  active   10.1.1.1  12.1.1.1      0      10     10

    SPAN Sessions
    Name    Status    DST Port    SRC Port    Direction    Queue    Policer
    ------  --------  ----------  ----------  -----------  -------  ---------
    sess1   active    Ethernet24  Ethernet32  rx


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
```
    # Get all mirror sessions
    # curl -X GET "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json"

    # Create SPAN session
    # curl -X POST "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json" -H "Content-Type: application/yang-data+json" -d "{ \"sonic-mirror-session:MIRROR_SESSION\": { \"MIRROR_SESSION_LIST\": [ { \"name\": \"sess1\", \"dst_port\": \"Ethernet10\", \"src_port\": \"Ethernet8\", \"direction\": \"rx\" } ] }}"

    # Delete all mirror sessions
    # curl -X DELETE "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session" -H "accept: application/yang-data+json"

    # Delete specific mirror session
    # curl -X DELETE "https://<switch_ip>/restconf/data/sonic-mirror-session:sonic-mirror-session/MIRROR_SESSION/MIRROR_SESSION_LIST=mirr3" -H "accept: application/yang-data+json"
```

### 3.5.7 GNMI Support

- Following GNMI set and get commands will be supported.
```
    # Get all mirror sessions
    # gnmi_get -xpath /sonic-mirror-session:sonic-mirror-session -target_addr 127.0.0.1:8080 -insecure

    # Create SPAN session. mirror.json includes json payload same as rest-api above.
    # gnmi_set -update /sonic-mirror-session:sonic-mirror-session/:@./mirror.json -target_addr 127.0.0.1:8080 -insecure

    # Delete all mirror sessions
    # gnmi_set -delete /sonic-mirror-session:sonic-mirror-session -target_addr 127.0.0.1:8080 -insecure

    # Delete specific mirror session
    # gnmi_set -delete /sonic-mirror-session:sonic-mirror-session/MIRROR_SESSION/MIRROR_SESSION_LIST[name=Mirror1] -target_addr 127.0.0.1:8080 -insecure
```
# 4 Flow Diagrams

# 5 Error Handling

- show mirror_session command will display any errors during session configuration and current status of session.
- Internal processing errors within SwSS will be logged in syslog with ERROR level
- SAI interaction errors will be logged in syslog

# 6 Serviceability and Debug

# 7 Warm Boot Support
The mirroring configurations be retained across warmboot so that source traffic gets mirrored properly to destination port.

# 8 Scalability

Max mirror sessions supported are silicon specific. 

###### Table 3: Scaling limits
|Name                      |   Scaling value    |
|--------------------------|--------------------|
| Max mirror sessions      | silicon specific   |

# 9 Unit Test

## 9.1 CLI Test Cases

This feature comes with a full set of virtual switch tests in SWSS.
| S.No | Test case synopsis                                                                                                                      |
|------|-----------------------------------------------------------------------------------------------------------------------------------------|
|  1   | Verify that session with only destination port can be created.                                                                          |
|  2   | Verify that session becomes active with single source, destination, direction.                                                          |
|  3   | Verify that session becomes active with multiple source ports.                                                                          |
|  4   | Verify that session becomes active with policer and destination port.                                                                   |
|  5   | Verify that session becomes active with source, destination, policer , queue config.                                                    |
|  6   | Verify that session becomes active with multiple source, different policer config.                                                      |
|  7   | Verify that session becomes active with LAG as source port.                                                                             |
|  8   | Verify that mirror config on LAG ports gets deleted when member port is deleted from LAG.                                                            |
|  9   | Verify that session can be created with multiple source ports and LAG ports.                                                            |
| 10   | Verify that ERSPAN session can be created with source ports.                                                                            |
| 11   | Verify that ERSPAN session becomes active when next hop is reachable and source port will be configured with mirror config.             |
| 12   | Verify that ERSPAN session with next hop on VLAN and source port will be configured with mirror config.                                 |
| 13   | Verify that ERSPAN session with next hop on LAG and source ports will be configured with mirror config.                                 |
| 14   | Verify that ERSPAN session with next hop on LAG and source port as LAG.                                                                 |
| 15   | Verify that mirror config on source LAG gets deleted when destination IP is not reachable.                                              |
| 16   | Verify that mirror config on source LAG gets deleted when destination IP on LAG becomes not reachable.                                  |
| 17   | Verify that ERSPAN mirror config on source LAG gets deleted when port is removed from portchannel                                       |
| 18   | Verify that rx/tx/both directions in SPAN mirror session.                                                                               |
| 19   | Verify that rx/tx/both directions in ERSPAN mirror session.                                                                             |


Sample virtual switch test outputs captured below.

```
platform linux2 -- Python 2.7.13, pytest-4.6.2, py-1.8.1, pluggy-0.13.1 -- /usr/bin/python
cachedir: .pytest_cache
rootdir: /home/brcm/tests
collected 12 items

test_mirror_port_erspan.py::TestMirror::test_PortMirrorERSpanAddRemove PASSED                                                                                                                                                          [  8%]
test_mirror_port_erspan.py::TestMirror::test_PortMirrorToVlanAddRemove PASSED                                                                                                                                                          [ 16%]
test_mirror_port_erspan.py::TestMirror::test_PortMirrorToLagAddRemove PASSED                                                                                                                                                           [ 25%]
test_mirror_port_erspan.py::TestMirror::test_PortMirrorDestMoveVlan PASSED                                                                                                                                                             [ 33%]
test_mirror_port_erspan.py::TestMirror::test_PortMirrorDestMoveLag PASSED                                                                                                                                                              [ 41%]
test_mirror_port_erspan.py::TestMirror::test_LAGMirrorToERSPANLagAddRemove PASSED                                                                                                                                                      [ 50%]
test_mirror_port_span.py::TestMirror::test_PortMirrorAddRemove PASSED                                                                                                                                                                  [ 58%]
test_mirror_port_span.py::TestMirror::test_PortMirrorMultiSpanAddRemove PASSED                                                                                                                                                         [ 66%]
test_mirror_port_span.py::TestMirror::test_PortMirrorPolicerAddRemove PASSED                                                                                                                                                           [ 75%]
test_mirror_port_span.py::TestMirror::test_PortMirrorPolicerMultiAddRemove PASSED                                                                                                                                                      [ 83%]
test_mirror_port_span.py::TestMirror::test_PortMirrorPolicerWithAcl PASSED                                                                                                                                                             [ 91%]
test_mirror_port_span.py::TestMirror::test_LAGMirorrSpanAddRemove PASSED                                                                                                                                                               [100%]
```