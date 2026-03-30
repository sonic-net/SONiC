# NHG Mgr LLD

# Overview

In the design of RIB/FIB, there is an extra FIB block in fpmsyncd. The NHG (Next Hop Group) Manager is designed to manage the entire FIB block. It is responsible for managing the mapping between Zebra RIB (Routing Information Base) Next Hop Groups and SONiC NHG Objects. The NHG Manager handles the creation, update, deletion, and dependency tracking of next hop groups to support efficient route convergence.

# Architecture

![arch.svg](images/arch.svg)
# Data Structures

![class.svg](images/class.svg)

## Enumerations

### sonicNhgObjType

**Usages**

Defines the type of SONiC NHG objects

**Value**

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| SONIC\_NHG\_OBJ\_TYPE\_NHG\_NORMAL | 0 | Standard next hop group |
| SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC | 1 | SRv6 VPN PIC Context |
| SONIC\_NHG\_OBJ\_TYPE\_MAX | 255 | Max type value |

## Structures

### SonicNHGObjectKey

**Usages**

*   Used as a hash key for all kinds of SONiC NHG objects. 
    

**Fields**

| **Field Name** | **Description** |
| --- | --- |
| groupMember | Vector of pairs <member\_id, weight> |
| nexthop | Next hop IP address string |
| vpnSid | VPN SID for SRv6 (type-specific) |
| segSrc | Segment source address |
| ifName | Interface name |
| type | SONiC NHG object type |

### SonicPICContentObject

**Usages**

*   Represents a SONiC PIC Content object. 
    

**Fields**

| Field Name | Type | Description |
| --- | --- | --- |
| type | sonicNhgObjType | Object type |
| groupMember | std::vector<pair<uint32\_t, uint32\_t>> | group members of NHG |
| nexthop | string | Next hop address |
| vpnSid | string | VPN SID for SRv6 |
| ifName | string | Interface name |
| segSrc | string | Segment source |
| ifIndex | uint32\_t | Interface index |
| id | uint32\_t | Sonic-assigned object ID |

### SonicNHGObjectInfo

**Usages:**

*   Tracks created SONiC NHG objects for reference counting


**Fields:**

| Field Name | Type | Description |
| --- | --- | --- |
| id | uint32\_t | Sonic NHG object ID |
| refCount | uint32\_t | Reference count of object |

## Class Specifications

### NHGMgr

**Purpose**

Main coordinator for NHG operations, Including all the creation and deletion related to NHG in FIB block, such as sending it to APP DB operation, exposing the interface for adding, deleting NHG and obtaining the corresponding NHG information.

**Usages**

Used as a private member of RouteSync class. Call the functions of NHG mgr to add or delete a zebra NHG, and get the SONiC NHG object info by zebra NHG id.

**Main Functions**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| addNHGFull() | NextHopGroupFull nhg, uint8\_t af | int | Add or update NHG from FIB block, triggered in onNextgroupFullMsg |
| delNHGFull() | uint32\_t id | int | Delete NHG from FIB block, triggered in onNextgroupFullMsg |
| getRIBNHGEntryByRIBID() | uint32\_t id | RIBNHGEntry\* | Retrieve RIB NHG entry by RIB ID, used in onRouteMsg to get the corresponding sonic id |
| getSonicPICByRIBID() | uint32\_t id | SonicPICContentEntry\* | Get SONiC PIC Content entry by rib NHG id, used in onRouteMsg to get the corresponding SONiC PIC Content object id |
| getSonicPICByID() | sonicNhgObjType type, uint32\_t id | SonicPICContentEntry\* | Get SONiC PIC Content entry by type and sonic object id |
| isSonicNHGIDInUsed() | uint32\_t id | bool | Check if Sonic NHG ID is in used |
| isSonicPICIDInUsed() | sonicNhgObjType type, uint32\_t id | bool | Check if Sonic PIC Content ID is in used |

**Main Members**

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| m\_rib\_nhg\_table | RIBNHGTable\* | Store all NHG information sent by RIB and the corresponding Sonic NHG info |
| m\_sonic\_pic\_table | SonicPICContentTable\* | Store all SONiC PIC Content objects created in FIB block, such as PIC Context object in SRv6 scenario. |
| m\_sonic\_id\_manager | SonicIDMgr | Manage Sonic Object ID allocation |

### RIBNHGTable

**Purpose**

Used to store and manage NHG information received from Zebra. 

**Usages**

Used as a private member of NHGMgr class. Call the functions of RIBNHGTable to add or delete a zebra entry, and get the SONiC NHG info by zebra NHG id.

**Main Functions**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| addEntry() | NextHopGroupFull nhg, uint8\_t af | int | Add or update NHG from FIB block, triggered in onNextgroupFullMsg |
| delEntry() | uint32\_t id | int | Delete NHG from FIB block, triggered in onNextgroupFullMsg |
| updateEntry() | NextHopGroupFull nhg, uint8\_t af, bool &updated | int | Update existed RIB entry, return true if entry has updates. |
| getEntry() | uint32\_t id | RIBNHGEntry\* | Retrieve RIB NHG entry by RIB ID, used in onRouteMsg to get the corresponding SONiC NHG id or nexthop fields |
| isNHGExist() | uint32\_t id | bool | Check if NHG entry exists in table by rib ID |
| writeToDB() | RIBNHGEntry \*entry | int | Persist entry to APP\_DB,NEXTHOP\_GROUP\_TABLE |
| removeFromDB() | uint32\_t id | None | Remove the NHG entry from APP\_DB,NEXTHOP\_GROUP\_TABLE |
| cleanUp() | None | None | Clean up all entries in the table |
| insertCreatedSharedNHGObject() | SonicNHGObjectKey key, uint32\_t id | None | Insert shared Sonic NHG Object into m\_created\_shared\_nhg\_map |
| insertCreatedNhgObject() | uint32\_t sonicNhgId, uint32\_t ribNhgId | None | Insert created Sonic NHG Object into m\_sonic\_nhg\_id\_2\_rib\_nhg\_id\_map |
| getCreatedSharedNHGObjectID() | SonicNHGObjectKey key | int | Get created Sonic NHG Object ID from m\_created\_shared\_nhg\_map, return 0 if not exist |
| addSonicNHGObjectRef() | SonicNHGObjectKey key | None | Add reference count for shared Sonic NHG Object |
| subSonicNHGObjectRef() | SonicNHGObjectKey key | None | Sub reference count for shared Sonic NHG Object, remove if refCount is 0 |

**Main Members**

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| m\_nhg\_map | map<uint32\_t, RIBNHGEntry\*> | RIB ID to entry mapping |
| m\_created\_shared\_nhg\_map | map<SonicNHGObjectKey, SonicNHGObjectInfo> | Tracking all shared Sonic NHG Object created in FIB block |
| m\_sonic\_nhg\_id\_2\_rib\_nhg\_id\_map | map<uint32\_t, uint32\_t> | Store Sonic NHG Object ID to RIB NHG ID mapping, not include shared NHG Object |
| m\_nexthop\_groupTable | ProducerStateTable | APP\_DB NEXTHOP\_GROUP\_TABLE interface |
| m\_sonic\_id\_manager | SonicIDMgr\* | Pointer to Sonic ID Manager |

### RIBNHGEntry

**Purpose**

Represents a single RIB NHG entry.

**Usages**

After receiving zebra message, create the corresponding entry and store it in RIBNHGTable. When processing route message, get the RIBNHGEntry through zebra id and get the converted SONiC id or NHG fields through the RIBNHGEntry.

**Main Functions**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| getFvVector() | None | vector<FieldValueTuple> | Get the fv vector of the entry. Used when create SONiC NHG object. |
| getSonicObjID() | None | uint32\_t | Get the SONiC NHG obj id. Used to get the SONiC NHG id in route message process. |
| getSonicPICObjID() | None | uint32\_t | Get the SONiC PIC Content obj id. Used to get the SONiC PIC Content obj id in route message process. |
| getSonicObjType() | None | sonicNhgObjType | Get the sonic object type of the entry. |
| hasSonicPICObj() | None | bool | Check if the entry has sonic PIC Content object. |
| needCreateSonicObject() | None | bool | Check if the entry needs to create sonic NHG object in APP DB. |
| isSingleNexthop() | None | bool | Check if the entry is single nexthop. |
| isSharedSonicNHG() | None | bool | Check if the entry uses shared Sonic NHG. |
| isSRv6Nhg() | None | bool | Check if the entry has SRv6 information. |
| getSonicNHGObjectKey() | None | SonicNHGObjectKey | Get the SonicNHGObjectKey of the entry. |
| setSonicNHGObjId() | uint32\_t id | None | Set the Sonic NHG Object ID. |
| setSonicPICObjId() | uint32\_t id | None | Set the sonic PIC Content Object ID. |
| enableNHG() | None | None | Set the enable flag true. |
| disableNHG() | None | None | Set the enable flag false. |
| getNhgEnableStatus() | None | bool | Get the NHG enable status. |
| checkNeedUpdate() | NextHopGroupFull newNHG, uint8\_t newAF | bool | Check if entry needs update from new NextHopGroupFull. |
| createSonicPICContentObjectFromRIBEntry() | SonicPICContentObject &sonicNhgOut | int | Create SonicPICContentObject from RIBNHGEntry. |
| createSRv6PICObjFromRIBEntry() | SonicPICContentObject &sonicNhgOut | int | Create SonicPICContentObject for SRv6 PIC from RIBNHGEntry. |
| getNextHopStr()<br>...<br>getInterfaceNameStr() | None | string | Getters of NHG fields. Used to get the SONiC PIC Content obj id in route message process. |

**Main Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_rib\_id | uint32\_t | Zebra-assigned RIB NHG ID. |
| m\_sonic\_obj\_id | uint32\_t | SONiC-assigned NHG ID, 0 indicates no corresponding SONiC NHG object created. |
| m\_sonic\_pic\_obj\_id | uint32\_t | PIC Content Object ID (SRv6, Vxlan etc), 0 indicates no corresponding SONiC PIC Content object created. |
| m\_sonic\_obj\_type | sonicNhgObjType | Type of SONiC NHG object |
| m\_group | unordered\_map<uint32\_t, uint16\_t> | Full group <ribID, weight>. |
| m\_resolvedGroup | unordered\_map<uint32\_t, uint16\_t> | Resolved group. |
| m\_depends | set<uint32\_t> | RIB IDs this entry depends on. |
| m\_dependents | set<uint32\_t> | RIB IDs depending on this entry. |
| m\_nhg | NextHopGroupFull | Full NHG data from Zebra. |
| m\_ifName | string | Interface string of the NHG. |
| m\_nexthop | string | Nexthop string of the NHG. |
| m\_weight | string | Weight string of the NHG. |
| m\_af | uint8\_t | Address family of the entry. |
| m\_enable | bool | Enable flag of the entry, default true. Updated in back walk process. |
| m\_is\_single | bool | Single nexthop flag. |
| m\_is\_shared\_sonic\_nhg | bool | Shared Sonic NHG Object flag. |
| m\_has\_sonic\_pic\_obj | bool | Has sonic PIC Content Object flag. |
| m\_is\_srv6\_nhg | bool | True if with srv6 information or member with srv6 information. |
| m\_create\_sonic\_nhg\_obj | bool | Flag to indicate if need create sonic NHG object. |
| m\_sonic\_nhg\_key | SonicNHGObjectKey | Sonic NHG Object key of the entry. |

### SonicPICContentTable

**Purpose**

Store all kinds of SONiC PIC Content objects in the FIB block

**Usages**

Used as a private member of NHGMgr class. Call the functions of SonicPICContentTable to add or delete a object in addNHGFull or delNHGFull.

**Main Methods**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| addEntry() | SonicPICContentObject sonicObj | int | Add SONiC PIC Content entry. |
| delEntry() | sonicNhgObjType type, uint32\_t id | None | Delete SONiC PIC Content entry by type and id. |
| getEntry() | sonicNhgObjType type, uint32\_t id | SonicPICContentEntry\* | Get SONiC PIC Content entry by type and sonic object id. |
| writeToDB() | SonicPICContentEntry \*entry | int | Persist entry to APP\_DB |
| removeFromDB() | SonicPICContentEntry \*entry | None | Remove the SONiC PIC Content object from APP\_DB |
| cleanUp() | None | None | Clean up all entries in the table |

**Main Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_pic\_map | map<uint32\_t, SonicPICContentEntry \*> | Store created SONiC PIC Content entries, key is id in PIC\_CONTEXT\_TABLE. |
| m\_pic\_contextTable | ProducerStateTable | Interface of APP\_DB PIC\_CONTEXT\_TABLE. |

### SonicPICContentEntry

**Purpose**

Represents a single SONiC PIC Content entry.

**Usages**

Created in special scenarios, such SRv6 VPN.

**Main Functions**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| getFvVector() | None | vector<FieldValueTuple> | Get the fv vector of the entry. Used when create SONiC PIC Content object into APP DB. |
| getSonicPICContentObjKey() | None | SonicNHGObjectKey | Get the SonicNHGObjectKey. |
| getSonicPicContentObjId() | None | uint32\_t | Get the SONiC PIC Content obj id. |
| getType() | None | sonicNhgObjType | Get the type of the entry. |
| getObj() | None | SonicPICContentObject | Get the SonicPICContentObject. |
| getRefCount() | None | uint32\_t | Get the reference count. |

**Main Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_sonic\_obj\_key | SonicNHGObjectKey | SonicNHGObjectKey of this entry. |
| m\_sonic\_obj\_id | uint32\_t | SONiC PIC Content object ID, 0 indicates no corresponding sonic PIC Content object created |
| m\_sonic\_obj | SonicPICContentObject | SonicPICContentObject of this entry. |
| m\_group | set<pair<uint32\_t, uint32\_t>> | <id, weight> pairs of group member. |
| m\_ref\_count | uint32\_t | Reference count of the entry, default 1. |

### SonicIDMgr

**Purpose:** It may be necessary to create multiple types of SONiC NHG object in FIB block, and assign an ID to each type of object. We want to manage all types of ID assignment through one class. Adding a new SONiC NHG object only needs to add a new type of allocator in SonicIDMgr.

**Usages:** 

*   The SonicIDMgr class manages ID allocation across different SONiC NHG object types. Every type of SonicIDAllocator works for the ID assignment of one table in APP DB.

*   IDs start from 1 (0 is reserved for invalid).

*   Used as a private member of NHG mgr and initialized the supported type allocator.

*   Currently contains two types of SonicIDAllocator, one is m\_nhg\_id\_allocator indicated by type SONIC\_NHG\_OBJ\_TYPE\_NHG\_NORMAL, another is m\_pic\_id\_allocator indicated by type SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC.


**Main Functions**

| **Method** | **Input** | **Return** | **Description** |
| --- | --- | --- | --- |
| init() | vector supportObj | int | Create the allocator according to the input types. |
| allocateID() | sonicNhgObjType type | uint32\_t | Assign the ID according to the type, return value of 0 means failed. |
| freeID() | sonicNhgObjType type, uint32\_t id | None | Free the ID according to the type. |
| isSonicObjIDUsed() | sonicNhgObjType type, uint32\_t id | bool | Check if the id is in used for specific type. |

**Main Members**

| **Object Type** | **Allocator** |
| --- | --- |
| SONIC\_NHG\_OBJ\_TYPE\_NHG\_NORMAL | m\_nhg\_id\_allocator (APP\_NEXTHOP\_GROUP\_TABLE\_NAME) |
| SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC | m\_pic\_id\_allocator (APP\_PIC\_CONTEXT\_TABLE\_NAME) |

# SRv6 VPN Support

This section describes the additional features added to the PIC Content object to support SRv6 scenarios.

## sonicNhgObjType

Add SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC type to indicate the SRv6 VPN RIB NHG.

## RIBNHGEntry

**Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_vpnSid | string | Vpn sid string of the NHG. |
| m\_segSrc | string | Seg src string of the NHG |
| m\_is\_srv6\_nhg | bool | True if with srv6 information or member with srv6 information. |

**Functions**

| **Name** | **Description** |
| --- | --- |
| checkNeedCreateSonicPICObj() | Add the judgment of whether the received NHG is SRv6 NHG, set m\_sonic\_obj\_type and m\_has\_sonic\_pic\_obj. |
| syncFvVector() | Add the srv6 vpn fields sync for SRv6 NHG. |
| checkNeedCreateSonicNHGObj() | Add the judgment of whether create shared SONiC NHG for SRv6 NHG. |
| createSRv6PICObjFromRIBEntry() | Create SonicPICContentObject for SRv6 PIC from RIBNHGEntry. |

## SonicPICContentTable

**Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_pic\_map | map<uint32\_t, SonicPICContentEntry \*> | Map used to store the created SRv6 PIC Content entries. The key is pic context id. |
| m\_pic\_contextTable | ProducerStateTable | APP\_DB PIC\_CONTEXT\_TABLE interface |

**Functions**

| **Name** | **Description** |
| --- | --- |
| addEntry() | Support the SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC type SONiC PIC Content entry creation. |
| delEntry() | Support the SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC type SONiC PIC Content entry deletion. |
| writeToDB() | Support the SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC type object write into PIC\_CONTEXT\_TABLE. |
| removeFromDB() | Support the SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC type object remove from PIC\_CONTEXT\_TABLE. |

## SonicIDMgr

**Members**

| **Attribute** | **Type** | **Description** |
| --- | --- | --- |
| m\_pic\_id\_allocator | SonicIDAllocator\* | ID allocator for PIC\_CONTEXT\_TABLE. |

**Functions**

| **Name** | **Description** |
| --- | --- |
| allocateID() | Support the type of SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC. |
| freeID() | Support the type of SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC. |
| init() | Create the SonicIDAllocator for type of SONIC\_NHG\_OBJ\_TYPE\_NHG\_WITH\_SRV6\_PIC |

# Processing Flows

## addNHGFull Flow

![add_sequence_diagram.svg](images/add_sequence_diagram.svg)

1.   FIB block receives NextHopGroupFull from Zebra via addNHGFull()

2.  Check if NHG already exists in RIBNHGTable

3.   If new: call addNewNHGFull()

    1.  Create RIBNHGEntry and populate from NextHopGroupFull

    2.   Check if Sonic NHG object needs to be created in the APP DB

        1.    If needed: allocate Sonic ID via SonicIDMgr

        2.  Write to APP\_DB NEXTHOP\_GROUP\_TABLE

    3.    Check if SONiC PIC Content object needed (SRv6)

        1.  If needed: create SonicPICContentObject and write to PIC\_CONTEXT\_TABLE

4.  If exists: call updateExistingNHGFull()

    1.  Compare old and new NextHopGroupFull

    2.  Update RIBNHGEntry fields if changed

    3.  Handle dependency changes (add/remove dependents)

    4.  Update Sonic NHG object if key changed

    5.  Update SONiC PIC Content object if SRv6 fields changed


## delNHGFull Flow
![deletion_diagram.svg](images/deletion_diagram.svg)
1.  Receive delete request via delNHGFull(id)

2.  Verify entry exists and has no dependents

3.  Delete SONiC PIC Content object if exists (handle ref count)

4.  Remove SONiC NHG ref from created map

5.  Free SONiC NHG ID via SonicIDMgr

6.  Remove dependency relationships

7.  Delete RIBNHGEntry from RIBNHGTable


# How to support future features

## Warm reboot

*   Store the info in Nhg mgr before reboot.

*   Recover the Nhg mgr tables after reboot.

*   Map the zebra NHG and SONiC Object by zebra hash key and NHG fields


##  convergence

*   Support back walk and forward walk by depends and dependencies in RIBNHGEntry.

*   Add fields to enable or disable NHG in RIBNHGEntry.


## vxlan

*   Add new type of SONiC PIC Content object type for vxlan in Sonic