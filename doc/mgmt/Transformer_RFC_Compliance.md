# REST support for RFC Compliance

**High Level Design Document**

**Rev 0.5**

**Table of Contents**

- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Definition/Abbreviation](#definitionabbreviation)
- [1 Overview](#1-overview)
- [2 Requirements](#2-requirements)
	- [2.1 POST](#21-post)
	- [2.2 PUT](#22-put)
	- [2.3 PATCH (Merge)](#23-patch-merge)
	- [2.4 DELETE](#24-delete)
	- [2.5 GET](#25-get)
- [3 Detailed Design](#3-detailed-design)
	- [3.1 POST](#31-post)
	- [3.2 PUT](#32-put)
	- [3.3 PATCH](#33-patch)
	- [3.4 DELETE](#34-delete)
- [4 Unit Tests](#4-unit-tests)
	- [4.1 POST Operation](#41-post-operation)
	- [4.2 PUT Operation](#42-put-operation)
	- [4.3 PATCH Operation (Create/Merge)](#43-patch-operation-createmerge)
	- [4.4 DELETE Operation](#44-delete-operation)
	- [4.5 GET Operation](#45-get-operation)
- [Appendix - Notes for Feature Developers](#appendix---notes-for-feature-developers)
	- [1. PATCH for CLI config commands](#1-patch-for-cli-config-commands)
	- [2. Subscribe callback](#2-subscribe-callback)
	- [3. YANG extension - virtual-table](#3-yang-extension---virtual-table)
	- [4. XfmrSubscOutParams.isVirtualTbl flag](#4-xfmrsubscoutparamsisvirtualtbl-flag)
	- [5. Error type TranslibXfmrRetError](#5-error-type-translibxfmrreterror)
	- [6. Child subtree-xfmr invoked during DELETE on parent resource](#6-child-subtree-xfmr-invoked-during-delete-on-parent-resource)
	- [7. YANG extension - table-owner](#7-yang-extension---table-owner)
	- [8. GET operation](#8-get-operation)
	- [9. Container instantiation with default values](#9-Container-instantiation-with-default-values)
	- [10. Limited support on PUT Operation](#10-limited-support-on-put-operation)


# Revision

| **Rev** | **Date**   | **Author** | **Change Description**                           |
| ------- | ---------- | ---------- | ------------------------------------------------ |
| 0.0     | 06/29/2020 | Infra team | Initial version                                  |
| 0.1     | 07/14/2020 | Kwan Kim   | Update the section 5 Note for Feature developers |
| 0.2     | 07/15/2020 | Kwan Kim   | Update to resolve comments etc.                  |
| 0.3     | 07/15/2020 | Jeff Yin   | Fix formatting and grammar                       |
| 0.4     | 07/16/2020 | Kwan Kim   | Update the Appendix                              |
| 0.5     | 07/23/2020 | Kwan Kim   | Update the Appendix (PUT operation etc.)         |

# About this Manual

This document provides general information about the REST server support for [RFC 8040](https://tools.ietf.org/html/rfc8040) compliance.   

# Scope

This document describes the requirements for only SONiC management-framework related aspects. Hence, the design herein is not intended to be fully compliant with RFC 8040.


# Definition/Abbreviation

| **Resource**        | **Description**                                              |
| ------------------- | ------------------------------------------------------------ |
| datastore  resource | the "{+restconf}/data" subtree represents the  datastore resource, which is a collection of configuration data and state  data nodes. |
| data  resource      | a data resource represents a YANG data node that is a  descendant node of a datastore resource. |
| target  resource    | the resource that is associated with a particular message,  identified by the "path" component of the request URI |
| CRUD | Create, Replace, Update, Delete |



# 1 Overview

The sonic-mgmt-framework is not compliant with REST standard. This document defines the expected behavior and documents the infrastructure changes needed to become compliant. It also provides guidelines for feature developers to change CLI and callbacks with an RFC-compliant infrastructure.

The SONiC management-framework REST server provides CRUD operations accessing YANG-defined resources to be compliant with the following documents.

 YANG 1.1: https://tools.ietf.org/html/rfc7950
 RESTCONF: https://tools.ietf.org/html/rfc8040



# 2 Requirements

To support RFC compliance, there are several behavioral requirements for POST, PUT, PATCH, DELETE, and GET.

This section describes the specific ways that Transformer will conform to these requirements, as well as any needed deviations from the RFC.

## 2.1 POST

- Allowed target resource can be a container, list, or list instance; the payload has child resources for the given target resource.  
Note that a leaf or leaf-list cannot be a target resource. Such terminal nodes can be defined as child resources.
- https://tools.ietf.org/html/rfc8040#section-4.4
If the data resource already exists, then the POST request MUST fail and a "409 Conflict" status-line MUST be returned. The error-tag value "resource-denied" is used in this case.
But, in some cases like the below example, the POST needs be adjusted to proceed with a DB update after translation because it really adds PortChannel12 to Vlan600. This case would make xfmr callbacks hard to implement.
Hence, to avoid complexity, the implementation will deviate from the standard to make the POST method **idempotent** in order to yield consistent results like PUT in creating a resource.

      e.g.
      curl -X POST "https://10.52.139.213/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel12/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan" -H "accept: application/yang-data+json" -H "authorization: BasicYWRtaW46YnJvYWRjb20=" -H "Content-Type:     application/yang-data+json" -d "{     \"openconfig-vlan:config\": { \"interface-mode\":     \"ACCESS\", \"access-vlan\": 600 }}"

      I0501 14:33:08.765453 44684 common_app.go:416] Processing DB operation for map[2:map[4:map[VLAN:map[Vlan600:"members@":"PortChannel12"

- POST requires checking parent resource existence for the target URI. e.g in the above example, the parent resource "/[restconf/data/openconfig-interfaces:interfaces/interface=PortChannel12](https://10.52.139.213/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel12/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan)" MUST exist
      \- **need a method to check the URI paths for all operations (POST, PUT, PATCH and GET)**

- Return codes:
  - 201 (Created) if successful
  - 404 (Not found) otherwise

## 2.2 PUT

- Allowed target resource can be a container, list, list instance, leaf-list, or leaf.  
Note that leaf-list instance can not be a target resource
- If a target resource is a leaf-list, the PUT method only creates a leaf-list. It MUST NOT change the value of a leaf-list instance.

RESTConf does not support a "rename" operation for leaf-list nodes, meaning you cannot replace the value of a leaf-list node -- you can only delete it and then re-create with a new value.

```
e.g. the instance "1" & "5" exists. then, the below method add the "11".

PUT /restconf/data/a/b/leaf-list

{"leaf-list": [11]}
 The result of the operation is [["1", "11", "5"] stored in CONFIG_DB.
```

- No support for "insert" and "point" query parameter for list or leaf-list with "ordered-by user"

- Replacing a datastore resource is not supported, i.e. PUT datastore resource "restconf/data" to replace the entire configuration
- Unlike the target resource for the POST method, where it is the parent of the new resource, the target resource for the PUT (or PATCH) method for resource creation is the new resource.
- Like POST, the PUT method also requires checking parent resource existence for the target URI.
- Return codes:
  - If the PUT request creates a new resource, a "201 Created" status-line is returned.
  - If an existing resource is modified, a "204 No Content" status-line is returned.
  - 404 (Not found) otherwise

## 2.3 PATCH (Merge)

- Allowed target resources are the same as PUT
- If the target resource instance does not exist, the server MUST NOT create it.

```
       e.g. no Vrf_1
       curl -X PATCH "https://localhost/restconf/data/sonic-vrf:sonic-vrf/VRF/VRF_LIST=Vrf_1/vni" -H "accept:     application/yang-data+json" -H "Content-Type:     application/yang-data+json" -d "{ \"sonic-vrf:vni\":     10}"e.g.

       e.g. : attempt to add data vrf
       curl -k -X PATCH "https://10.11.57.9/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf_10/config"     -H "accept: application/yang-data+json" -H "Content-Type:     application/yang-data+json" -d "{     "openconfig-network-instance:config": { "name":     "Vrf_10", "type": "L3VRF",     "enabled": false }}"

```

- Return codes:
  - 200 Ok
  - 204 No Content
  - 404 Not Found

## 2.4 DELETE

- Allowed target resources: container, list, list instance, leaf-list, leaf-list instance, or leaf.

- If a list-instance or container is deleted, the associated hash key and fields need to be removed

- If a leaf or leaf-list is deleted as a last node to the parent container or list instance, the associated hash key should be retained with "NULL"/"NULL" field.

- Return codes:
  - 204 ”No Content” if successful
  - 404 "Not Found" otherwise

- Deviation: Considering that not all OC-YANG leafy nodes are mapped to CONFIG_DB, it would be consistent to return OK, i.e. "204 No Content", for both OC/IETF and SONiC YANG, for all three below cases to avoid overhead.

  1.  URI points to leaf/leaf-list and that leaf/leaf-list field is **not yet configured** in DB table instance
   - eg. /sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST=Vrf_test1/**coalesce_time**
   - eg. /sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST=Vrf_test1/**confed_peers**

   DB table instance contents showing "coalesce_time" and "confed_peer" fields haven't been configured:
   ```
   hgetall BGP_GLOBALS|Vrf_test1
   1) "confed_id"
   2) "323"
   ```

  2.  URI points to leaf-list instance/item , and that **item doesn't exist in leaf-list** contents in DB table instance:
   - eg. /sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST=Vrf_test1/confed_peers=**525**

   DB table instance contents showing "525" value-item not configured in leaf-list contents:
```
   hgetall BGP_GLOBALS|Vrf_test1
   1) "confed_id"
   2) "323"
   3) "confed_peers@"
   4) "323,1,4294"
```

  3. URI points to leaf-list instance/item, and the **leaf-list doesn't exist** in DB table instance
   - eg. /sonic-bgp-global:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST=Vrf_test1/confed_peers=525

   DB table instance contents showing "confed_peer" field hasn't been configured:
   ```
   hgetall BGP_GLOBALS|Vrf_test1
   1) "confed_id"
   2) "323"
   ```

## 2.5 GET

- Allowed target resource: container, list, list instance, leaf-list, leaf-list instance, or leaf.

- Below cases are handled with a slight deviation from the standard to return 200(OK) or 404(Not found)

1.   GET operation, where the URI points to a nested list instance:

  eg. `/openconfig-XYZ/containerA/listA=instance123/containerB/listB=instance456`

   A. listA, instance123 does NOT exist – return code 404

   B. listA, instance123 does exist, but listB, instance456 does not exist – return code 404

2.   GET operation, where the URI points to entire list, and no instance exists in DB since nothing has been configured yet

  eg. `/openconfig-XYZ/containerA/listA`: return code 200

3.   GET operation, where the URI points to a container, mapping to same table as parent list, and spans some fields in that table

  eg. `/openconfig-XYZ/containerA/listA=instance123/containerB`

   A. listA, instance123 does NOT exist in table mapped– return code 404

   B. listA, instance123 does exist, but all fields under containerB do not exist in table instance corresponding to listA=instance123 – return code 200

4.   GET operation, where the URI points to leaf-list instance, and leaf-list instance does NOT exist in table, since it was not configured yet, return code 404

  eg. `https://10.11.56.28/restconf/data/ietf-snmp:snmp/vacm/view=TestVacmView1/include=1.2.3.*`

  DB contents showing leaf-list instance does NOT exist :
```
  hgetall SNMP_SERVER_VIEW| TestVacmView1

      1) "include@"
      2) "1.8.9.*,1.7.9.*"
```
5.  GET operation, where the URI points to a leaf-list instance, but leaf-list field itself does NOT exist in table, since it was not configured yet – return code 404

  eg. `https://10.11.56.28/restconf/data/ietf-snmp:snmp/vacm/view=TestVacmView1/include=1.2.3.*`

  DB contents showing leaf-list field itself does NOT exist :
```
  Hgetall SNMP_SERVER_VIEW| TestVacmView1

      1) "name”
      2) "testName"
```

6.   GET operation, where the URI points to whole leaf-list, but leaf-list field itself does NOT exist in table, since it was not configured yet – return code 200

  eg. `https://10.11.56.28/restconf/data/ietf-snmp:snmp/vacm/view=TestVacmView1/include`

  DB contents showing leaf-list field itself does NOT exist :

```
  hgetall SNMP_SERVER_VIEW| TestVacmView1

      1) "name”
      2) "testName"
```

7.   GET operation, where the URI points to a leaf, but leaf/field itself does NOT exist in table, since it was not configured yet – return code 404

# 3 Detailed Design

Below is the detail design for Transformer to support the requirements defined in the section 2.

**NOTE:** yangDefValDbDataMap mentioned in WorkItem column is applicable only for OC-YANG and **NOT** for sonic-yang.

## 3.1 POST

(Req: 1)  allowed target resource can be a container or list or list instance: the payload has child resources for the given resource

(Req: 2)  Note that leaf or leaf-list can not be a target resource. Such terminal nodes can be defined as child resources.

(Req: 3)  "If the data resource already exists, then the POST request MUST fail and a "409 Conflict" status-line MUST be returned. The error-tag value "resource-denied" is used in this case." -  to avoid the complexity, the proposed option is to make **idempotent** POST method to yield consistent result as PATCH in creating a resource. `note that db.CreateEntry(k,v)uses HMSET(fields in v)`

(Req: 4)  The POST requires checking parent resource existence for the target URI. e.g in the above example, the parent resource "/[restconf/data/openconfig-interfaces:interfaces/interface=PortChannel12](https://10.52.139.213/restconf/data/openconfig-interfaces:interfaces/interface=PortChannel12/openconfig-if-aggregate:aggregation/openconfig-vlan:switched-vlan)" MUST be existent
        \- **need a method to check the URI paths for all operations (POST, PUT, PATCH and GET)**

(Req: 5)  Target resource for resource creation should be the parent of the new resource(i.e. payload).

| **S.No** | **Requirement** | **Target resource**                                 | **Payload**                                          | **Redis-DB  contents**                       | **Expected behavior / action**                               | **Return code**       | **WorkItem**                                                 |
| -------- | --------------- | --------------------------------------------------- | ---------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------ | --------------------- | ------------------------------------------------------------ |
| 1        | Req: 2          | URI ending with leaf or leaf-list.                  | Data resources for the given target resource.        | Data  may or may not be present in DB.       | Error:  Operation not allowed                                | Error                 |                                                              |
| 2        | Req:  1, Req: 3 | URI ending with container or list or list instance. | Child data resources for the given target resource.  | Data(instance  level) already present in DB. | Convert  yang data to dbDataMap.    Change oper to UPDATE and write to DB i.e. update existing instance. | Success: 201   Error: | Infra needs to be enhanced to return 2 dbDataMaps having    (i) user specified data contents(dbDataMap).   (ii) create new dataMap(yangDefValDbDataMap) for fields with yang default  value if not present in incoming data.   (iii) write the contents of dbDataMap or both the dbDataMap  & yangDefValDbDataMap based on the use case. |
| 3        | Req:  1, Req: 3 | URI ending with container or list or list instance. | Child data resources for the given target resource.  | Data  not present in DB.                     | Convert yang data to dbDataMap & create yangDefValDbDataMap and write  to DB i.e create new instance. | Success: 201   Error: |                                                              |
| 4        | Req:  4         | URI ending with container or list or list instance. | Child data  resources for the given target resource. | Parent data present in DB.                   |                                                              | Success: 201          | Infra needs to be enhanced  to split the request URI at each list level, fetch the table & key at  that level and check its existance in db. |
| 5        | Req:  4         | URI ending with container or list or list instance. | Child data resources for the given target resource.  | Parent  data not present in DB.              | Reject  this request.                                        | Error:                |                                                              |
| 6        | Req:  1, 5      | URI ending with container or list or list instance. | Data resources for the given target resource.        | Data may or may not  be present in DB.       | Reject  this request.                                        | Error:                |                                                              |


## 3.2 PUT
(Req: 1)  Allowed target resource can be a container or list or list instance or leaf-list or leaf. Note that leaf-list instance can not be a target resource. If a target resource is a leaf-list, the PUT method only creates a leaf-list, MUST NOT change the value of leaf-list instance.

(Req: 2)  Target resource for resource creation should be of the new resource. That is, the target URI should be matched with data resource to be created or replaced.

(Req: 3)  Like POST, the PUT also requires checking parent resource existence for the target URI.

**Notes:**

- No support     for "insert" and "point" query parameter for list or     leaf-list with "ordered-by user"
- Replace     datastore resource is not supported, i.e. datastore resource     "restconf/data" to replace entire configuration

| **S.No** | **Requirement** | **Target resource**                                         | **Payload**                                                  | **Redis-DB  contents**                 | **Expected behavior / action**                               | **Return code**       | **WorkItem**                                                 |
| -------- | --------------- | ----------------------------------------------------------- | ------------------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------ | --------------------- | ------------------------------------------------------------ |
| 1        | Req: 1, Req: 2  | URI ending with container or list or list instance or leaf. | Data resources for the given target resource.                | Data  already present in DB.           | Convert  yang data to dbDataMap & create yangDefValDbDataMap. Replace the existing  instance content in DB with the new data. | Success: 201   Error: | Infra needs to be enhanced to return 2 dbDataMaps  having    (i) user specified data contents(dbDataMap).   (ii) create new dataMap(yangDefValDbDataMap) for fields with yang default  value if not present in incoming data.   (iii) write the contents of dbDataMap or both the dbDataMap  & yangDefValDbDataMap based on the use case. |
| 2        | Req:  1, Req: 2 | URI ending with container or list or list instance or leaf. | Data resources for the given target resource.                | Data  not present in DB.               | Convert  yang data to dbDataMap & create yangDefValDbDataMap and create new  instance. | Success: 201   Error: |                                                              |
| 3        | Req:  1, Req: 2 | URI ending with leaflist.                                   | Data resources for the given target resource.                | Data  already present in DB.           | Convert yang data to dbDataMap & oper to UPDATE. Merge with the  existing instance content in DB with the new data. | Success: 201   Error: |                                                              |
| 4        | Req:  1, Req: 2 | URI ending with leaflist.                                   | Data  resources for the given target resource.               | Data not present in DB.                | Convert  yang data to dbDataMap create new instance.         | Success: 201   Error: |                                                              |
| 5        | Req:  1, Req: 2 | URI ending with container or list or list instance.         | Child data resources for the given target resource.          | Data  may or may not be present in DB. | Reject  this request.                                        | Error                 |                                                              |
| 6        | Req:  3         | URI ending with container or list or list instance or leaf. | Data resources for the given target resource.                | Parent data not present in  DB.        | Reject  this request.                                        | Error                 | Infra  needs to be enhanced to split the request URI at each list level, fetch the  table & key at that level and check its existance in db. |
| 7        |                 | URI ending with container or list or list instance.         | Data resources for the given target resource with child data. | Data may or may not  be present in DB. | Convert yang data to dbDataMap & create  yangDefValDbDataMap.    ( i ) Replace the existing instance content, if present in DB with the new  data.   (ii) update the existing instance content in DB with the new data. |                       | Currently  supported in infra, need to test this usecase.    |



## 3.3 PATCH

(Req: 1) Allowed target resource is same as PUT. i.e. Allowed target resource can be a container or list or list instance or leaf-list or leaf. Note that leaf-list instance can not be a target resource. If a target resource is a leaf-list, the PUT method only creates a leaf-list, MUST NOT change the value of leaf-list instance.  

(Req: 2) If the target resource instance does not exist, the server MUST NOT create it.

(Req: 3) Like POST, the PATCH also requires checking parent resource existence for the target URI.

| **S.No** | **Requirement** | **Target resource**                                          | **Payload**                                                  | **Redis-DB  contents**                 | **Expected behavior / action**                               | **Return code** | **WorkItem**                                                 |
| -------- | --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------ | --------------- | ------------------------------------------------------------ |
| 1        | Req: 1, Req: 2  | URI ending with container or list or list instance or leaf or  leaflist. | Data resources for the given target resource.                | Data  already present in DB.           | Convert  yang data to dbDataMap. Update the existing instance content in DB with the  new data. | Success: 200    |                                                              |
| 2        | Req:  1, Req: 2 | URI ending with container or list or list instance or leaf or  leaflist. | Data resources for the given target resource.                | Data  not present in DB.               | Reject  this request.                                        | Error: 404      |                                                              |
| 3        | Req:  1, Req: 2 | URI ending with container or list or list instance.          | Child data resources for the given target resource.          | Data  may or may not be present in DB. | Reject this request.                                         | Error:          |                                                              |
| 4        | Req:  3         | URI ending with container or list or list instance or leaf.  | Data  resources for the given target resource.               | Parent data not present in  DB.        | Reject  this request.                                        | Error           | Infra needs to be enhanced  to split the request URI at each list level, fetch the table & key at  that level and check its existance in db.  Infra  needs to be enhanced to return 2 dbDataMaps having    (i) user specified data contents(dbDataMap).   (ii) create new dataMap(yangDefValDbDataMap) for fields with yang default  value if not present in incoming data.   (iii) read the db to check if the instance exist, if not use  the dbDataMap & yangDefValDbDataMap and create.   (iv) if instance exist, update it. |
| 5        |                 | URI ending with container or list or list instance.          | Data resources for the given target resource with child data. | Data  not present in DB.               | Convert yang data to dbDataMap & create yangDefValDbDataMap.    ( i ) create new instance, if not already present with data in dbDataMap  & yangDefValDbDataMap.  (ii) update the existing instance content in DB with  the new data. |                 |                                                              |



## 3.4 DELETE

(Req: 1) allowed target resource: container, list, list instance, leaf-list, leaf-list instance, leaf.

(Req: 2) if a list-instance or container is deleted, the associated hash key and fields need be removed

(Req: 3) if a leaf or leaf-list is deleted as a last node to the parent container or list instance, the associated hash key should be retained with "NULL"/"NULL" field.

| **S.No** | **Requirement**         | **Target resource**                                          | **Payload** | **Redis-DB  contents**  | **Expected behavior / action**                               | **Return code**      | **WorkItem**                                                 |
| -------- | ----------------------- | ------------------------------------------------------------ | ----------- | ----------------------- | ------------------------------------------------------------ | -------------------- | ------------------------------------------------------------ |
| 1        | Req: 1                  | URI ending with container.                                   | N/A         | Data  present in DB.    | Delete  all the leaves inside the container.                 | Success: 200  Error: | Infra  needs to be enhanced to delete only the redis table fields mapping to the  yang leaves inside the container. |
| 2        | Req:  1, Req: 2         | URI ending with list instance.                               | N/A         | Data  present in DB.    | Delete list instance key and its associated fields.          | Success: 200  Error: |                                                              |
| 3        | Req:  1                 | URI ending with leaf or leaflist.                            | N/A         | Data  present in DB.    | Delete field.                                                | Success: 200  Error: |                                                              |
| 4        | Req:  3                 | URI ending with container or leaf or leaflist.               | N/A         | Data present in DB.     | Delete the leaf/leaflist and the contents of the container. If  it the last field in that table-instance, retain the list instance. | Success: 200  Error: | Infra needs to be enhanced  to add "NULL"/"NULL"  field to retain the table instance, if the all the contents in that instance  is deleted. |
| 5        | Req:  1, Req: 2, Req: 3 | URI ending with container or list instance or leaf or  leaflist. | N/A         | Data not present in DB. |                                                              | Error:404            |                                                              |



# 4 Unit Tests

## 4.1 POST Operation

\-     POST - uri: container, message-body: leaf and leaf-list, return 201 (Created)

\-     POST - uri: list, message-body: list instance wth leaf and leaf-list, return 201 (Created)

\-     POST - uri: list instance, message-body: leaf and leaf-list, return 201 (Created)

\-     POST - Idempotetnt POST, return 201 (Created)

\-     POST - uri: container, but parent instance not existent, return 404 (Not found)

\-     POST - uri: list instance, but the list instance not existent, return 404

\-     POST - uri: leaf, message-body: leaf, return 400(Bad Request)

\-     POST - uri: leaf-list, message-body: leaf-list, return 400(Bad Request)



## 4.2 PUT Operation

\-     PUT(create) uri: container, message-body: container, leaf and leaf-list, return 201(Created)

\-     PUT(create) uri: list, message-body: list, instance, leaf and leaf-list, return 201(Created)

\-     PUT(create) uri: list instance, message-body: list instance, leaf and leaf-list, return 201(Created)

\-     PUT(create) uri: leaf, message-body: leaf, return 201(Created)

\-     PUT(create) uri: leaf-list, message-body: leaf-list, return 201(Created)

\-     PUT(replace) uri: container, message-body: container, leaf and leaf-list, return 204(No Content) for resource modification

\-     PUT(replace) uri: list, message-body: list, instance, leaf and leaf-list, 204(No Content) for resource modification

\-     PUT(replace) uri: list instance, message-body: list instance, leaf and leaf-list, return 204(No Content)

\-     PUT uri: list instance, but message-body has a diffent instance, return 400 (Bad Request)

\-     PUT with uri: container, but parent instance not existent, return 400 (Bad Request)


## 4.3 PATCH Operation (Create/Merge)

\-     PATCH(create) uri: container, message-body: container, leaf and leaf-list, - 204(No Content)

\-     PATCH(create) uri: list, message-body: list, instance, leaf and leaf-list

\-     PATCH(create) uri: list instance, message-body: list instance, leaf and leaf-list

\-     PATCH(create) uri: leaf, message-body: leaf

\-     PATCH(create) uri: leaf-list, message-body: leaf-list

\-     PATCH(merge), fill some other nodes or override existing ones

\-     PATCH with uri list instance that is not existent, return 404(Not Found)



## 4.4 DELETE Operation

\-     DELETE uri container - 204(No Content)

\-     DELETE uri list - 204(No Content)

\-     DELETE uri list instance - 204(No Content)

\-     DELETE uri leaf - 204(No Content)

\-     DELETE uri leaf-list - 204(No Content)

\-     DELETE uri leaf-list instance - 204(No Content)

\-     DELETE with uri: list instance not existent - 404(Not Found)

\-     DELETE with uri: leaf not existent - 204(No Content)

\-     DELETE with uri: leaf-list not existent - 204(No Content)

\-     DELETE with uri: leaf-list instance not existent - 204(No Content)



## 4.5 GET Operation

\-     GET with uri container, but no data nodes existent, return code - 200(Ok), with empty body

\-     GET with uri list, but no instances existent- 200(Ok), with empty body

\-     GET with uri leaf-list, but no instances existent -200(Ok), with empty body

\-     GET with uri OC list instance, and data exists- 200(Ok), with non-empty body

\-     GET with uri OC list instance/config, and data exists- 200(Ok), with non-empty body

\-     GET with uri container: parent list instance not existent, 404(Not Found)

\-     GET with uri list instance not existent, 404(Not Found)



# Appendix - Notes for Feature Developers

Notable fixes for RFC compliance support:
- For all the operations, the parent table check is enforced prior to data transformation
- PATCH operation fetches YANG default values for leafy (leaf/leaf-list) nodes if any, when a resource is created
- PUT can be used to create a resource, if its not existent in DB
- Delete on a terminal node(container/list) will delete the leafy objects from the Redis table without touching others. This will be incase of multi container contents mapping to a same table


###### 1. PATCH for CLI config commands

The PATCH operation works for most CLI config commands, since they usually create config once and merge afterwards.

A target resource is strictly checked for existence in the DB, so the CLI actioner should set a URI to the parent container to create and update a data resource when a list instance is created. This is because there is no need to check existence for a non-existent container.   

e.g. Create Vlan10 by PATCH on the URI set to /openconfig-interfaces:interfaces

```
curl -X PATCH "https://10.11.177.17/restconf/data/openconfig-interfaces:interfaces" -H "accept: application/yang-data+json" -H "Content-Type: application/yang-data+json" -d "{ \"openconfig-interfaces:interfaces\": { \"interface\": [ { \"name\": \"Vlan10\", \"config\": { \"name\": \"Vlan10\" } } ] }}"
```



###### 2. Subscribe callback

The transformer internally checks a target resource URI for all operations to ensure its existence in the server.

e.g. Vrf_10 should exist in CONFIG_DB to process the PATCH operation.

```
curl -k -X PATCH "https://10.11.57.9/restconf/data/openconfig-network-instance:network-instances/network-instance=Vrf_10/config" -H "accept: application/yang-data+json" -H "Content-Type: application/yang-data+json" -d "{ "openconfig-network-instance:config": { "name": "Vrf_10", "type": "L3VRF", "enabled": false }}"
```

A rule of thumb to check a target resource -

If a subtree xfmr is annotated on the path, you MUST have a subscribe subtree-xfmr implemented to return the tables mapped at the given URI to perform an existence check.  The subscribe subtree-xfmr is intended for use by the infra to perform the existence check.
Otherwise, table-xfmr/key xfmr or table-name/key-name along with DB number must be there to return table names for the given URI.

Note that there is no need to annotate YANG extension for subscribe subtree-xfmr.

e.g. `/oc-sys:system/oc-sys:ntp/oc-sys:servers/oc-sys:server` has subtree-transformer.

```
    deviation /oc-sys:system/oc-sys:ntp/oc-sys:servers/oc-sys:server {
        deviate add {
            sonic-ext:subtree-transformer "ntp_server_subtree_xfmr";
        }
    }
```

Below is an example code of subscribe subtree-xfmr for the above path.  The subscribe callback will be invoked before any other callback by the Transformer to determine the existence for the target resource. The returned **dbDataMap** should have DB number, table and keys specific to the given uri that can be mapped to Redis table and key.

```go
var Subscribe_ntp_server_subtree_xfmr = func(inParams XfmrSubscInParams) (XfmrSubscOutParams, error) {
        var err error
        var result XfmrSubscOutParams
        result.dbDataMap = make(RedisDbMap)

        pathInfo := NewPathInfo(inParams.uri)

        targetUriPath, _ := getYangPathFromUri(pathInfo.Path)

        keyName := pathInfo.Var("address")

        log.Infof("Subscribe_ntp_server_subtree_xfmr path %v key %v ", targetUriPath, keyName)

        if (keyName != "") {
                result.dbDataMap = RedisDbMap{db.ConfigDB:{NTP_SERVER_TABLE_NAME:{keyName:{}}}}
                log.Infof("Subscribe_ntp_server_subtree_xfmr keyName %v dbDataMap %v ", keyName, result.dbDataMap)
        } else {
                result.dbDataMap = RedisDbMap{db.ConfigDB:{NTP_SERVER_TABLE_NAME:{"*":{}}}}
                log.Infof("Subscribe_ntp_server_subtree_xfmr keyName %v dbDataMap %v ", keyName, result.dbDataMap)
        }
        result.isVirtualTbl = false
        /* Please refer to Note 3.
        result.needCache = true
        result.nOpts = new(notificationOpts)
        result.nOpts.mInterval = 15
        result.nOpts.pType = OnChange
        */
        log.Info("Returning Subscribe_ntp_server_subtree_xfmr")
        return result, err
}
```

- Note 1 - if the URI points to a list without keys, then the key of returned dbDataMap needs to be set to "\*".
- Note 2 - if there is no mapping table at all, please refer to the section 3 and 4 below.
- Note 3 - the request URI contains multiple parent lists, the subscribe xfmr will be invoked per parent list.
- Note 4 - The fields - needCache, onChange, nOpts.mInterval, nOpts.pType - are specific to on-change subscription. As of now, on-change subscription is allowed for only terminal container, list, leaf & leaf-list. Hence, these fields are not applicable to the subscribe callback associated to not-immediate parent lists.

If multiples keys (instances) are returned from a subscribe callback, you can return with "\*".

e.g. `/openconfig-qos:qos/scheduler-policies/scheduler-policy` has subtree-transformer.

Request path("/openconfig-qos:qos/scheduler-policies/scheduler-policy[name=sp1]/schedulers/scheduler[sequence=2]/two-rate-three-color/config/cir")

Note that, in the above example, the key "sp1" and "2" gets contatenated to make a DB key, "SCHEDULER|sp1@2".   
The subscribe callback will be invoked at both scheduler-policy[name=sp1] and scheduler[sequence=2] in this order.
At scheduler-policy[name=sp1], the subscribe-xfmr has to return table="SCHEDULER" and key="sp1\*" because the seqeunce 2 is not known at this level. The infra will perform pattern based query using "sp1\*" to ensure resource existence.
Subsequently, at scheduler[sequence=2], the subscribe-xfmr has to return table="SCHEDULER", key="sp1@2".


###### 3. YANG extension - virtual-table

In cases where there is no matching table in the DB schema for Openconfig YANG list/container, a new yang extension `virtual-table` can be used to instruct the Transformer to skip checking for table presence. By default, the virtual-table is set to `False`.

e.g. `intf_subintfs_table_xfmr` and `intf_subintfs_xfmr` map to `SUBINTF_TBL` table & `index` key respectively, but this table/key does not reside in CONFIG_DB. In this case, you can set `sonic-ext:virtual-table “True”` to skip the resource check.

```
   deviation /oc-intf:interfaces/oc-intf:interface/oc-intf:subinterfaces/oc-intf:subinterface {
     deviate add {
     	sonic-ext:table-transformer "intf_subintfs_table_xfmr";
    	sonic-ext:key-transformer "intf_subintfs_xfmr";
    	sonic-ext:virtual-table “True”
     }
   }
```

​		e.g. there is no mapping table to /oc-netinst:network-instances/oc-netinst:network-instance/oc-netinst:protocols/oc-netinst:protocol

```
    deviation /oc-netinst:network-instances/oc-netinst:network-instance/oc-netinst:protocols/oc-netinst:protocol {
        deviate add {
            sonic-ext:table-transformer "network_instance_protocols_ptotocol_table_name_xfmr";
            sonic-ext:key-transformer "network_instance_protocol_key_xfmr";
            sonic-ext:virtual-table "true";
        }
    }
```



###### 4. XfmrSubscOutParams.isVirtualTbl flag

In addition to YANG extension virtual-table, app developers may also have to programmatically ask the infra to skip the resource check because there is no table mapping available for a certain target resource.  The type `XfmrSubscOutParams` is returned from the subscribe subtree callback. You can set the `isVirtualTbl` flag to `true` if the resource check needs to be skipped.



```go
type XfmrSubscOutParams struct {
    dbDataMap RedisDbMap
    needCache bool
    onChange bool
    nOpts *notificationOpts  //these can be set regardless of error
    isVirtualTbl bool //used for RFC parent table check, set to true when no Redis Mapping
}
```

e.g. below path can be mapped to both Redis table and dataset (e.g. sensor) fetched from Host via DBus. Hence your subscribe callback can set the `isVirtualTbl` to `false` if the URI points to the sensor.

```
    deviation /oc-platform:components/oc-platform:component {
      deviate add {
        sonic-ext:subtree-transformer "pfm_components_xfmr";
      }
    }
```

Here is example code to set the `isVirtualTbl` flag:

```go
var Subscribe_pfm_components_xfmr SubTreeXfmrSubscribe = func (inParams XfmrSubscInParams) (XfmrSubscOutParams, error) {
    var err error
    var result XfmrSubscOutParams
    key := NewPathInfo(inParams.uri).Var("name")
    mstr := strings.ToLower(key)    if key == "" || mstr == "sensor" {
        /* no need to verify dB data if we are requesting ALL
           components or if request is for sensor */
        result.isVirtualTbl = true
        return result, err
    }
    result.dbDataMap = make(RedisDbMap)
    if mstr == "system eeprom" {
        result.dbDataMap = RedisDbMap{db.StateDB: {EEPROM_TBL:{"*":{}}}}
    } else if mstr == "software" {
        /* software component reads from XML file but also
         * gets EEPROM information from dB */
        result.dbDataMap = RedisDbMap{db.StateDB: {EEPROM_TBL:{"*":{}}}}
    } else if validPsuName(&key) {
        result.dbDataMap = RedisDbMap{db.StateDB: {PSU_TBL:{key:{}}}}
    } else if validFanName(&key) {
        result.dbDataMap = RedisDbMap{db.StateDB: {FAN_TBL:{key:{}}}}
    } else if validTempName(&key) {
        result.dbDataMap = RedisDbMap{db.StateDB: {TEMP_TBL:{key:{}}}}
    } else if validXcvrName(&key) {
        result.dbDataMap = RedisDbMap{db.StateDB: {TRANSCEIVER_TBL:{key:{}}}}
    } else {
        return result, errors.New("Invalid component name")
    }    return result, err
}
```



###### 5. Error type TranslibXfmrRetError

New error type `TranslibXfmrRetError` is introduced for **key-xfmr/table-xfmr during DELETE operations.**

For the DELETE case, when we have a DELETE request at a container, the expected behavior is to delete the contents of the container and retain its table instance in the DB. In order to fulfill this behavior, the infra traverses the children nodes and fills the DbDataMap with the fields to be deleted. If the child container has a key/table xfmr function, it will be invoked to fetch the table and key. If the child table/key matches with that of the parent, then its contents/fields will be added to DbDataMap. Otherwise it will be ignored.

If the key/table xfmr returns error for the children, then the infra continues traversing to its siblings (default behavior). For any reason if the traversal needs to be stopped for an error returned from child key/table xfmr, then it needs to return `tlerr.TranslibXfmrRetError(xlateFailDelReq=true)`. This is a new tlerror introduced to tell the infra honor the application error and abort the transaction. Otherwise, the infra ignores the return error and move to the adjacent or descendant nodes. This is used to reduce the number of key/table xfmrs that is required to be changed by the app owners. The key/table transformers can look at the oper, requestUri, and uri in inParams and return appropriate values.

- Note 1 - this error type is only applicable to key-xfmr and table-xfmr.

- Note 2 - for CRU and GET, the infra will continue to handle the errors returned from all the xfmr functions, terminate the transaction, and report an app error to client

###### 6. Child subtree-xfmr invoked during DELETE on parent resource

If a subtree-xfmr is present along the hierarchy, all child subtree xfmrs are invoked for the request URI. If an error is returned from the invoked subtree xfmr function(s), it will be honored to terminate the transaction to report an app error to client.

The support to invoke the child subtree-xfmr function, for all parent level DELETE request has been added recently. Please go through your subtree-xfmr function(s) and see if you are handling parent level DELETE requests appropriately.

You can refer to the oper and requestUri in inParams to get the context i.e. operation-type & parent-uri (i.e., requestUri).



###### 7. YANG extension - table-owner

In case multiple target resources are mapped to a single table in CONFIG_DB, you can prevent table key deletion from DELETE operation on a certain target resource that is allowed only for field deletion.

The new YANG extension `table-owner` is introduced to restrict the DELETE operation on the URI mapped to the table key. By default, the `table-owner` is set to `“True”`.

Apps using other module tables to update its data (which themselves are not the owner of it), should be annotated with the `table-owner` annotation. This enables the infra to delete only the fields and not the table-instance.

 e.g. oc-relay YANG data resides in INTERFACE table and oc-relay is not the owner of that table. DELETE operation on `/oc-relay:relay-agent/oc-relay:dhcpv6/oc-relay:interfaces/oc-relay:interface=Ethernet4` would otherwise lead to delete the fields, enable and helper-address that pertain to the interface Ethernet4.

```
   deviation /oc-relay:relay-agent/oc-relay:dhcpv6/oc-relay:interfaces/oc-relay:interface {

   deviate add {
        sonic-ext:table-transformer "relay_agent_table_xfmr";
        sonic-ext:key-transformer "relay_agent_intf_tbl_key_xfmr";
        sonic-ext:table-owner "False”;
     }
   }
```



###### 8. GET operation

When a REST request points to a URI on either leaf or leaf-list-**instance** (NOT entire leaf-list), and if there is a field-transformer or subtree-transformer annotated at this level, then the existence check of that leaf or leaf-list instance MUST be performed by the Transformer callback. If the field/leaf-list-instance doesn’t exist, then the callback should return tlerr – `Resource not found`.

NOTE : Callback should return such an error only when a REST query points directly to a leaf or leaf-list instance. Only in such cases for GET operations will the error be propagated to NBI.


###### 9. Container instantiation with default values

In YANG model based RESTCONF/NETCONF server, the non-presence container is instantiated with default values at the startup time. But, in SONiC, since there is no OC YANG based data instantiation at startup time, the infra runs in lazy mode in instantiating container. That is, when the REST operation is requested to create leafy nodes under a container at the 1st time, the infra creates a DB entry with default values if defined in OC YANG.

e.g.

```
curl -X PATCH "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/global/config/as" -H "accept: application/yang-data+json" -H "authorization: Basic YWRtaW46c29uaWNAZGVsbA==" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-network-instance:as\": 5}" -k
```

After successful creation, CONFIG_DB will have

```
127.0.0.1:6379[4]> hgetall BGP_GLOBALS|default
1) "local_asn"
2) "100"
3) "holdtime"
4) "180"
5) "keepalive"
6) "60"
7) "network_import_check"
8) "true"
127.0.0.1:6379[4]>
```



###### 10. Limited support on PUT Operation

The PUT operation could involve replacing a given subtree with a new message body. But for now, the infra provides the limited support along a data tree hierarchy as shown in the below table A.

Example for case 1 - the PUT method will be used to replace only the contents of conatiner openconfig-bfd:enable-bfd/config.

```
curl -X PUT "https://localhost/restconf/data/openconfig-network-instance:network-instances/network-instance=default/protocols/protocol=BGP,bgp/bgp/neighbors/neighbor=11.1.1.1/openconfig-bfd:enable-bfd/config" -H "accept: application/yang-data+json" -H "authorization: Basic YWRtaW46c29uaWNAZGVsbA==" -H "Content-Type: application/yang-data+json" -d "{\"openconfig-bfd:config\":{\"enabled\":true,\"openconfig-bgp-ext:bfd-check-control-plane-failure\":true}}" -k
```

Table A - Cases to support PUT

![PUT cases](images/PUT_cases.jpg)
