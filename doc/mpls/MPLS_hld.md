# MPLS and Weighted ECMP Routes for SONiC High Level Design Document #

## Table of Content
- [MPLS and Weighted ECMP Routes for SONiC High Level Design Document](#mpls-and-weighted-ecmp-routes-for-sonic-high-level-design-document)
  - [Table of Content](#table-of-content)
    - [Revision](#revision)
    - [Scope](#scope)
    - [Definitions/Abbreviations](#definitionsabbreviations)
    - [Overview](#overview)
    - [Requirements](#requirements)
      - [Functional requirements](#functional-requirements)
      - [Configuration and Management requirements](#configuration-and-management-requirements)
      - [Scalability Requirements](#scalability-requirements)
      - [Warm Boot Requirements](#warm-boot-requirements)
      - [Future Requirements](#future-requirements)
    - [Architecture Design](#architecture-design)
    - [High-Level Design](#high-level-design)
      - [Overview](#overview-1)
      - [Database Changes](#database-changes)
        - [APPL DB](#appl-db)
          - [INTERFACE_TABLE](#interface_table)
          - [ROUTE_TABLE](#route_table)
          - [LABEL_ROUTE_TABLE](#label_route_table)
      - [Software Modules](#software-modules)
        - [NetLink](#netlink)
          - [Functions](#functions)
        - [IntfMgr](#intfmgr)
        - [FPM Syncd](#fpm-syncd)
          - [Functions](#functions-1)
        - [IntfsOrch](#intfsorch)
          - [Functions](#functions-2)
        - [RouteOrch](#routeorch)
          - [Functions](#functions-3)
        - [NeighOrch](#neighorch)
          - [Functions](#functions-4)
        - [Label/LabelStack](#labellabelstack)
        - [NextHopKey](#nexthopkey)
        - [Syncd](#syncd)
    - [SAI API](#sai-api)
      - [Router Interface](#router-interface)
      - [MPLS](#mpls)
      - [Next Hop](#next-hop)
      - [Next Hop Group](#next-hop-group)
    - [Configuration and management](#configuration-and-management)
      - [CLI Enhancements](#cli-enhancements)
      - [Config DB Enhancements](#config-db-enhancements)
        - [INTERFACE](#interface)
        - [PORTCHANNEL_INTERFACE](#portchannel_interface)
    - [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
    - [Restrictions/Limitations](#restrictionslimitations)
    - [Testing Requirements/Design](#testing-requirementsdesign)
      - [Unit Test cases](#unit-test-cases)
      - [System Test cases](#system-test-cases)
    - [Open/Action items - if any](#openaction-items---if-any)
### Revision
|  Rev  | Date  |  Author  | Change Description |
| :---: | :---: | :------: | ------------------ |
|  0.1  |       | A Pokora | Initial version    |

### Scope

This document provides general information about the MPLS feature implementation in SONiC.

### Definitions/Abbreviations
| Abbreviation | Description                           |
| ------------ | ------------------------------------- |
| cRPD         | Containerized Routing Protocol Daemon |
| ECMP         | Equal Cost Multi-Path                 |
| MPLS         | Multi-Label Packet Switching          |

### Overview

This document provides general information about the MPLS feature implementation in SONiC.

### Requirements

This section describes the SONiC requirements for:
- MPLS routes feature.
- Weighted ECMP routes feature.

#### Functional requirements
- Support to enable/disable MPLS per Interface.
- Support for MPLS Push, Pop, and Swap routes.
- Support for weighted ECMP routes for IPv4/IPv6 and MPLS.
- Support for bulk MPLS route programming.
- Integration with Juniper cRPD routing stack.
- Integration with Juniper SAI support.

#### Configuration and Management requirements
- SONiC CLI support for MPLS enable/disable per Interface.
- cRPD CLI support for MPLS route configuration.
- cRPD CLI support for weighted ECMP route configuration.
- cRPD CLI support for operational commands.

#### Scalability Requirements
- Up to max ASIC capable MPLS routes are supported.
- Error is logged in syslog for all attempted MPLS routes after max limit is reached.

#### Warm Boot Requirements
- MPLS functionality continues across warm reboot.
- Weighted ECMP functionality continues across warm reboot.
- Support for planned system warm restart.
- Support for SWSS docker warm restart.

#### Future Requirements
- Support for VRFs
- SONiC CLI support for operational commands.
- Integration with FRR routing stack.
- Integration with VS SAI.

### Architecture Design

The MPLS feature extends Route and Next Hop support in SONiC to include optional MPLS label stack in addition to the existing IPv4/IPv6 address information.
The weighted ECMP feature extends Next Hop Group support in SONiC to include optional weight in addition to the existing Next Hop Group Member information.

### High-Level Design

#### Overview
![Overview diagram](images/MPLS_overview_diagram.png "Overview of MPLS components")

**Figure 1: Overview of the data flow and related components of MPLS**

#### Database Changes
This section describes the modifications to SONiC Databases to support MPLS and weighted ECMP routes.

##### APPL_DB
The existing INTERFACE_TABLE is enhanced to accept a new "mpls" enable/disable attribute.

###### INTERFACE_TABLE
``` rfc5234
INTERFACE_TABLE|{{interface_name}}
    "mpls":{{enable|disable}} (OPTIONAL)

; Defines schema for MPLS configuration attribute
key                         = INTERFACE:ifname             ; Interface name
; field                     = value
mpls                        = "enable" / "disable"         ; Enable/disable MPLS function. Default disable
```

The existing ROUTE_TABLE for IPv4/IPv4 prefix routes is enhanced to accept:
- An optional MPLS label stack component in the existing "nexthop" attribute.
- An optional new "weight" attribute.
###### ROUTE_TABLE
``` rfc5234
"ROUTE_TABLE":{{prefix}}
    "nexthop":{{nexthop_list}}
    "ifname":{{ifname_list}}
    "weight":{{weight_list}} (OPTIONAL)

; Defines schema for IPv4/IPv6 route table attributes
key                         = ROUTE_TABLE:prefix       ; IPv4/IPv6 prefix
; field                     = value
nexthop                     = nexthop_list             ; List of nexthops.
ifname                      = ifname_list              ; List of interfaces.
weight                      = weight_list              ; List of weights.
;value annotations
ifname                      = 1*64VCHAR                ; name of the Interface (Port Channel)

```

A new LABEL_ROUTE_TABLE is introduced for MPLS routes to accept the same attributes as ROUTE_TABLE:
- A "nexthop" attribute with optional MPLS label stack component.
- A "ifname" attribute.
- An optional new "weight" attribute.
###### LABEL_ROUTE_TABLE
``` rfc5234
"LABEL_ROUTE_TABLE":{{mpls_label}}
    "nexthop":{{nexthop_list}}
    "ifname":{{ifname_list}}
    "weight":{{weight_list}} (OPTIONAL)

; Defines schema for MPLS label route table attributes
key                         = LABEL_ROUTE_TABLE:mpls_label ; MPLS label
; field                     = value
nexthop                     = STRING                   ; Comma-separated list of nexthops.
ifname                      = STRING                   ; Comma-separated list of interfaces.
weight                      = STRING                   ; Comma-separated list of weights.
```

#### Software Modules
This section describes modifications to software modules to support MPLS and weighted ECMP routes.
##### NetLink
Netlink is an existing open source library imported to SONiC.
Modifications to the existing NetLink implementation were needed to support MPLS routes.
###### Functions
New accessors were added to retrieve the MPLS NH destination and TTL values:
```
  /* Accessor to retrieve MPLS destination */
  extern struct nl_addr *	rtnl_route_nh_get_encap_mpls_dst(struct rtnl_nexthop *);
  /* Accessor to retrieve MPLS TTL */
  extern uint8_t		rtnl_route_nh_get_encap_mpls_ttl(struct rtnl_nexthop *);
```
##### IntfMgr
IntfMgr is an existing daemon in SWSS container that monitors operations in CONFIG DB on INTERFACE and PORTCHANNEL_INTERFACE tables.
IntfMgr now additionally processes the "mpls" attribute and propagates this attribute to APPL DB.

##### FPM Syncd
FPM Syncd is an existing daemon in BGP container that monitors NetLink messages from the SONiC routing stack.
FPM Syncd now additionally processes MPLS related Route and Next Hop information in the NetLink messages and sets this information in the APPL DB.
###### Functions
The following are new functions for fpmsyncd:
```
  /* Handler for rtnl messages with MPLS route */
  void RouteSync::onLabelRouteMsg(int nlmsg_type, struct nl_object *obj);
  /* Handler to process ECMP Weight information rtnl messages */
  string RouteSync::getNextHopWt(struct rtnl_route *route_obj);
```
##### IntfsOrch
IntfsOrch is an existing component of the OrchAgent daemon in the SWSS container.  IntfsOrch monitors operations on Interface related tables in APPL_DB and converts those operations into SAI commands to manage the Router Interface object.
###### Functions
The following are new functions for IntfsOrch:
```
  /* Handler to enable/disable MPLS per Interface */
  bool IntfsOrch::setRouterIntfMpls(Port& port)
```
##### RouteOrch
RouteOrch is an existing component of the OrchAgent daemon in the SWSS container.  RouteOrch monitors operations on Route related tables in APPL DB and converts those operations in SAI commands to manage Route and Inseg entries.  Additionally RouteOrch coordinates Next Hop object operations with NeighOrch and converts operations into SAI commands to manage Next Hop Group objects.
###### Functions
The following are new functions for RouteOrch:
```
  /* Consumer handler for all events in APPL_DB LABEL_ROUTE_TABLE */
  void RouteOrch::doLabelTask(Consumer& consumer);
  /* Handler to process new MPLS route from LABEL_ROUTE_TABLE */
  bool addLabelRoute(LabelRouteBulkContext& ctx, const NextHopGroupKey&);
  /* Handler to process MPLS route removal from LABEL_ROUTE_TABLE */
  bool removeLabelRoute(LabelRouteBulkContext& ctx);
```
##### NeighOrch
NeighOrch is an existing component of the OrchAgent daemon in the SWSS container.  NeighOrch monitors operations on Neighbor related tables in APPL_DB.  Additionally NeighOrch coordinates Next Hop operations with RouteOrch and converts operations into SAI commands to manage Next Hop objects.
###### Functions
The following are new functions for NeighOrch:

##### Label/LabelStack
Label and LabelStack are new type utilities of the OrchAgent daemon in the SWSS container.
These types are used to represent the MPLS label or label stack when found in a route or next hop.
```
typedef uint32_t Label;
class LabelStack
{
    ... class definition abbreviated ...
private:
    std::set<Label> m_labelstack;
};

```
##### NextHopKey
NextHopKey is an existing utility of the OrchAgent daemon in the SWSS container.  NextHopKey is used by both RouteOrch and NeighOrch to coordinate Next Hop operations.
NextHopKey class is modified to include LabelStack and weight member data.
```
struct NextHopKey
{
    LabelStack          label_stack;    // MPLS label stack
    IpAddress           ip_address;     // neighbor IP address
    string              alias;          // incoming interface alias
    uint8_t             weight;         // NH weight for NHGs
    ... struct definition abbreviated ...
};
```
##### Syncd
Syncd is an existing daemon of the Syncd container which handles all events driven by the ASIC_DB.
Modifications were made to fully support sairedis handling of the existing SAI MPLS API key: sai_inseg_entry_t.
```
/**
 * @brief In segment entry
 */
typedef struct _sai_inseg_entry_t
{
    /**
     * @brief Switch ID
     *
     * @objects SAI_OBJECT_TYPE_SWITCH
     */
    sai_object_id_t switch_id;

    /**
     * @brief MPLS label
     */
    sai_label_id_t label;

} sai_inseg_entry_t;
```

### SAI API

This section describes SAI APIs used to support MPLS and weighted ECMP routes.

#### Router Interface
Full details about current SAI Router Interface API and attributes are described here:
https://github.com/opencomputeproject/SAI/blob/master/inc/sairouterinterface.h

To facilitate MPLS functionality, the following update was made to the SAI Router Interface API:
```
    /**
     * @brief Admin MPLS state
     *
     * @type bool
     * @flags CREATE_AND_SET
     * @default false
     */
    SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE,
```
#### MPLS
Full details about current SAI MPLS API and attributes are described here:
https://github.com/opencomputeproject/SAI/blob/master/inc/saimpls.h

The entirety of the existing SAI MPLS API definition is now introduced to SONiC orchagent to facilitate MPLS route functionality.

Additionally, the following has been added to the SAI MPLS API defintion for to facilitate bulk MPLS route operations for capable platforms:
```
/**
 * @brief Bulk create In Segment entry
 *
 * @param[in] object_count Number of objects to create
 * @param[in] inseg_entry List of object to create
 * @param[in] attr_count List of attr_count. Caller passes the number
 *    of attribute for each object to create.
 * @param[in] attr_list List of attributes for every object.
 * @param[in] mode Bulk operation error handling mode.
 * @param[out] object_statuses List of status for every object. Caller needs to
 * allocate the buffer
 *
 * @return #SAI_STATUS_SUCCESS on success when all objects are created or
 * #SAI_STATUS_FAILURE when any of the objects fails to create. When there is
 * failure, Caller is expected to go through the list of returned statuses to
 * find out which fails and which succeeds.
 */
typedef sai_status_t (*sai_bulk_create_inseg_entry_fn)(
        _In_ uint32_t object_count,
        _In_ const sai_inseg_entry_t *inseg_entry,
        _In_ const uint32_t *attr_count,
        _In_ const sai_attribute_t **attr_list,
        _In_ sai_bulk_op_error_mode_t mode,
        _Out_ sai_status_t *object_statuses);

/**
 * @brief Bulk remove In Segment entry
 *
 * @param[in] object_count Number of objects to remove
 * @param[in] inseg_entry List of objects to remove
 * @param[in] mode Bulk operation error handling mode.
 * @param[out] object_statuses List of status for every object. Caller needs to
 * allocate the buffer
 *
 * @return #SAI_STATUS_SUCCESS on success when all objects are removed or
 * #SAI_STATUS_FAILURE when any of the objects fails to remove. When there is
 * failure, Caller is expected to go through the list of returned statuses to
 * find out which fails and which succeeds.
 */
typedef sai_status_t (*sai_bulk_remove_inseg_entry_fn)(
        _In_ uint32_t object_count,
        _In_ const sai_inseg_entry_t *inseg_entry,
        _In_ sai_bulk_op_error_mode_t mode,
        _Out_ sai_status_t *object_statuses);

/**
 * @brief Bulk set attribute on In Segment entry
 *
 * @param[in] object_count Number of objects to set attribute
 * @param[in] inseg_entry List of objects to set attribute
 * @param[in] attr_list List of attributes to set on objects, one attribute per object
 * @param[in] mode Bulk operation error handling mode.
 * @param[out] object_statuses List of status for every object. Caller needs to
 * allocate the buffer
 *
 * @return #SAI_STATUS_SUCCESS on success when all objects are removed or
 * #SAI_STATUS_FAILURE when any of the objects fails to remove. When there is
 * failure, Caller is expected to go through the list of returned statuses to
 * find out which fails and which succeeds.
 */
typedef sai_status_t (*sai_bulk_set_inseg_entry_attribute_fn)(
        _In_ uint32_t object_count,
        _In_ const sai_inseg_entry_t *inseg_entry,
        _In_ const sai_attribute_t *attr_list,
        _In_ sai_bulk_op_error_mode_t mode,
        _Out_ sai_status_t *object_statuses);

/**
 * @brief Bulk get attribute on In Segment entry
 *
 * @param[in] object_count Number of objects to set attribute
 * @param[in] inseg_entry List of objects to set attribute
 * @param[in] attr_count List of attr_count. Caller passes the number
 *    of attribute for each object to get
 * @param[inout] attr_list List of attributes to set on objects, one attribute per object
 * @param[in] mode Bulk operation error handling mode
 * @param[out] object_statuses List of status for every object. Caller needs to
 * allocate the buffer
 *
 * @return #SAI_STATUS_SUCCESS on success when all objects are removed or
 * #SAI_STATUS_FAILURE when any of the objects fails to remove. When there is
 * failure, Caller is expected to go through the list of returned statuses to
 * find out which fails and which succeeds.
 */
typedef sai_status_t (*sai_bulk_get_inseg_entry_attribute_fn)(
        _In_ uint32_t object_count,
        _In_ const sai_inseg_entry_t *inseg_entry,
        _In_ const uint32_t *attr_count,
        _Inout_ sai_attribute_t **attr_list,
        _In_ sai_bulk_op_error_mode_t mode,
        _Out_ sai_status_t *object_statuses);
```
The existing sai_mpls_api_t structure has been expanded to accommodate the new MPLS bulking APIs:
```
/**
 * @brief MPLS methods table retrieved with sai_api_query()
 */
typedef struct _sai_mpls_api_t
{
     sai_create_inseg_entry_fn                      create_inseg_entry;
     sai_remove_inseg_entry_fn                      remove_inseg_entry;
     sai_set_inseg_entry_attribute_fn               set_inseg_entry_attribute;
     sai_get_inseg_entry_attribute_fn               get_inseg_entry_attribute;

+    sai_bulk_create_inseg_entry_fn                 create_inseg_entries;
+    sai_bulk_remove_inseg_entry_fn                 remove_inseg_entries;
+    sai_bulk_set_inseg_entry_attribute_fn          set_inseg_entries_attribute;
+    sai_bulk_get_inseg_entry_attribute_fn          get_inseg_entries_attribute;

} sai_mpls_api_t;
```
#### Next Hop
Full details about SAI Next Hop API and attributes are described here:
https://github.com/opencomputeproject/SAI/blob/master/inc/sainexthop.h

No modifications were mode to the current SAI Next Hop API definition.

The following existing attribute is now introduced to SONiC orchagent to facilitate MPLS route functionality:
```
    /**
     * @brief Push label
     *
     * @type sai_u32_list_t
     * @flags MANDATORY_ON_CREATE | CREATE_ONLY
     * @condition SAI_NEXT_HOP_ATTR_TYPE == SAI_NEXT_HOP_TYPE_MPLS
     */
    SAI_NEXT_HOP_ATTR_LABELSTACK,
```
#### Next Hop Group
Full details about SAI Next Hop Group API and attributes are described here:
https://github.com/opencomputeproject/SAI/blob/master/inc/sainexthopgroup.h
To facilitate weighted ECMP route functionality, the following update was made to the SAI Next Hop Group API:
```
    /**
     * @brief Member weights
     *
     * @type sai_uint32_t
     * @flags CREATE_AND_SET
     * @default 1
     */
    SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT,
```

### Configuration and management
This section should have sub-sections for all types of configuration and management related design. Example sub-sections for "CLI" and "Config DB" are given below. Sub-sections related to data models (YANG, REST, gNMI, etc.,) should be added as required.

#### CLI Enhancements

A new command is introduced to configure interfaces for MPLS.

    # Enable/disable MPLS per INTERFACE.
    config interface mpls add|remove <intf-name>

#### Config DB Enhancements

The existing INTERFACE table is enhanced to accept a new "mpls" enable/disable attribute.
##### INTERFACE
``` rfc5234
INTERFACE|{{ifname}}
    "mpls":{{enable|disable}} (OPTIONAL)

; Defines schema for MPLS configuration attribute
key                      = INTERFACE:ifname    ; Interface name
; value annotations
ifname                   = 1*64VCHAR           ; name of the Interface
; field                  = value
mpls                     = "enable"/"disable"  ; Enable/disable MPLS function. Default is disable
```

The existing PORTCHANNEL_INTERFACE table is enhanced to accept a new "mpls" enable/disable attribute.
##### PORTCHANNEL_INTERFACE
``` rfc5234
PORTCHANNEL_INTERFACE|{{ifname}}
    "mpls":{{enable|disable}} (OPTIONAL)

; Defines schema for MPLS configuration attributes
key                      = PORTCHANNEL_INTERFACE:ifname   ; Port Channel Interface name
;value annotations
ifname                   = 1*64VCHAR                      ; name of the Interface (Port Channel)
; field                  = value
mpls                     = "enable"/"disable"             ; Enable/disable MPLS function. Default disable
```

### Warmboot and Fastboot Design Impact
MPLS design will not affect warmboot or fastboot design.

### Restrictions/Limitations
In this document, MPLS support is only for static lsp route support. The scope of routing stack supporting dynamic creation of MPLS tunnel is not in the design.

### Testing Requirements/Design
Using external routing controller to set up static lsp route for push/pop/swap operation on MPLS traffic and verify traffic is passing.

#### Unit Test cases
- Using Juniper cRPD set push operation lsp, observe ip traffic goes through router and egress side will have MPLS format with correct label.
- Using Juniper cRPD set pop operation lsp, observe mpls with single label traffic goes through router and egress side will have IP packets.
- Using Juniper cRPD set swap operation lsp, observe mpls traffic goes through router and egress side will have MPLS format with different label.
#### System Test cases
Not available
### Open/Action items - if any
None
