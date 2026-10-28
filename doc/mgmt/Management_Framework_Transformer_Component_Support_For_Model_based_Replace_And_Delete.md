# Model Based Replace & Delete In Mgmt-Framework Transformer

## Rev 0.1

# Table of Contents
  - [Revision](#revision)
  - [About This Manual](#about-this-manual)
  - [Scope](#scope)
  - [1 Feature Overview](#1-feature-overview)
  - [2 Background](#2-background)
  - [3 Requirements](#3-requirements)
  - [4 Design Overview](#4-design-overview)
    - [4.1 Example use cases](#41-example-use-cases)
  - [5 Yang annotation and callback considerations for feature apps](#5-yang-annotation-and-callback-considerations-for-feature-apps)
  - [6 Unit Tests](#6-unit-tests)
   

# Revision
| Rev |     Date    |       Author            | Change Description                |
|:---:|:-----------:|:-----------------------:|-----------------------------------|
| 0.1 | 03/10/2025  |   Kwan, Amruta, Ranjini | Initial version                   |

# About this Manual
This document provides general information about the model based replace and delete functionality support in SONiC mgmt-framework's transformer component.

# Scope
This document describes the overiew of the open config model based replace and delete functionality to be supported in transformer infra, and yang extensions & callback considerations required by the applications using the transformer infra.
Support for model based replace for sonic yang will be added in future.

# 1 Feature Overview
The PUT/REPLACE RESTCONF method represents operation equivalent to NETCONF "create" or "replace", that can be used to create non-existing data resources as well as to replace existing data resources with request payload. 
The DELETE operation is used to delete the target data resource including data resources under the target data resource yang hierarchy.
The data resource is identified by the RESTCONF target resource URI that can be at any depth of a yang data model hierarchy.

# 2 Background
Replacing data resource with PUT operation at any depth of YANG model has been a challenge over the last few releases and there was limited support to replace only the data translated from the request payload instead of entire data resource yang hierarchy.
Current DELETE operation resulted in the deletion of only the target data resource and not the heirarchy beneath it.
This feature attempts to overcome this behaviour and support the PUT & DELETE at any yang depth and avoid the applications to handle this in their callbacks especially the post transformer callback.

# 3 Requirements

- The PUT method should continue to be used to support resource creation or replacement.
- The PUT method should be used to replace data resources at any depth of YANG node tree.
- After PUT transaction completion, reading back/GET on the target resource should return only the new data present in PUT requestpayload, optionally with default values.
- The DELETE method should delete target data resource including data resources under the target data resource yang hierarchy.
- Descendant nodes that are not relevant to the parent instance in the request should not be affected.

# 4 Design overview

1) The PUT/REPLACE request will be processed as follows:

    - 1.1 The input json payload is traversed and will be translated to the corresponding tables, keys and fields identified by the infra through the application annotations.
        1. For a list node mapped to a table, it iterates all the instances available in the json payload and identifies them to be replaced /created along the tree with the data available in the payload.
           List instances present in the payload, just as an enclosing/wrapper complex node and having no leaves/attribute/data for the corresponding table-instance except the key leaf will result in either create or replace of table-instance with NULL/NULL field if there are no defaults to be applied.
           Nested nodes will follow the rest of the procedure as detailed in this section.
        2. For URI target ending in list-instance which doesn't exist in DB , it will be created apart from what is translated from payload.
        3. For container node mapped to a single entry, it is targeted to replace/create that entry with data available in the payload.For  
           container nodes present in the payload, just as an enclosing/wrapper complex node and having no leaves/data for the corresponding table-instance will result in create/replace of table-instance IFF there are defaults to be applied. If there are no defaults then such a table-instance will cease to exist if its a table owner, if not table-owner then only the container attributes will be deleted.Nested nodes will follow the same behavior.
        4. Defaults will be applied only for table-key instance translated from a complex node present in payload.This complex node will be traversed to identify the defaults and the scope is limited until a child complex node belonging to a different table spawning a new scope.Refer example 7 in the use cases section 4.1 below. 
        5. If tables are owned by multiple nodes as well as a target tree, all table entries belonging to a target instance are  updated with the payload without changing the fields that do not belong to the target yang hierarchy.
        6. Subtrees will continue to be invoked for the data available in the payload as in the current design. 
   
    - 1.2 The yang hierarchy from the target URI will be traversed by the infra to identify the tables / instances that are not part of the payload and marked to be deleted.
        1. The instances to be deleted will be identified by doing a GET like traversal of "config true" nodes and by the data learnt from the annotations.
        2. For non table owners the fields that are part of the table that belong to the yang hierarchy are marked for delete.
        3. For table owners the complete instance/ table entry will be identified for delete.
        4. Virtual tables will be skipped to be deleted and will be used only for yang hierarchy traversal.
        5. Subtree callbacks along the traversal path will be invoked and result from them will be merged with infra generated data (existing behaviour)
        6. All the tables / instances identified for delete will be merged with the final result of REPLACE processing as identified in Step 1.1, before we start the DB operations.

2) The DELETE request from northbound will follow the same procedures as point 1.2 in REPLACE flow as detailed above except 1.2)6) which is not required for north bound DELETE operation.

3) Current annotation of "get-validate" will be changed to "validate-xfmr"so that it can be used for CRUD cases as well as GET. During traversal both for REPLACE and DELETE flow, validate transformer callbacks will be invoked and if they identify the node to be not valid for the request, the node and its child heirarchy will not be processed.

4) The DB operations for all the tables in the final translated map will be continued to be excercised alongside CVL as in the current design.

After completion of PUT/REPLACE operation, a GET operation should find/fetch only the data releavent to the new config data asked by the client in the request payload.Similarly after completion of DELETE operation, a GET operation should fetch no data. 

**Limitations:** 
1.  Defaults will be applied only for DB instances mapped to the nodes in PUT payload and its child heirarchy belonging to the same table.Refer 1.1 4) above.
2. No default values will be applied when fields/DB table instances having default value are marked for delete in the GET-like delete flow (for both PUT and DELETE operations).Refer example 7 in the use cases section 4.1 below.
If the north bound operation is DELETE and when the target node is a leaf having default, the default value will be reset instead of deleting the leaf node (existing behavior).

## 4.1 Example use cases
Following are some case studies that demonstrate PUT functionality :

<table>
<tr>
<th>Case</th>
<th>URI and Yang Metadata     </th> 
<th>URI And Payload</th>
<th>DB content before</th>
<th>DB content after</th>
<th>Notes</th>
</tr>
<tr>

<td>
<pre>
1. URI target is Terminal 
container (has only child 
leaves)contents of container 
and all its children nodes 
are part of the same table.
(partial replace case)
<pre>
</td>
<td>
<pre>
/M/L[] { table-X  
 keys: k
 CA {
  leaves:m,n 
   C1 {
    leaves:a,b,g(def)      
   }
   C2 {
    leaves: c,d
   }
   C3 {
    leaves: e,f
   }
 }
}
</pre>
</td>
<td>
<pre>
M/L=val-k/CA/C1
payload : 
C1 {
 a = <b>Nval-a</b>,
 b = <b>Nval-b</b>
}
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
a : <b>val-a</b>
b : <b>val-b</b>
g : <b>val-g1</b>
c : val-c
d : val-d
e : val-e
f : val-f
m: val-m
n: val-n
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
a : <b>Nval-a</b>
b : <b>Nval-b</b>
g : <b>val-g</b> (reset default)
c : val-c
d : val-d
e : val-e
f : val-f
m: val-m
n: val-n
</pre>
</td>
<td>
<pre>  
Existing behaviour
</pre>
</td>
</tr>
</pre>

 <td>
<pre>
2. URI target is 
  non-terminal container.
  Contents of container and 
  all its child containers
  are part of the same table.
<pre>
</td>
<td>
<pre>
/M/L[] { table-X  
 keys: k
 CA {
  leaves:m,n 
   C1 {
    leaves:a,b,g(def)      
   }
   C2 {
    leaves: c,d
   }
   C3 {
    leaves: e,f
   }
 }
}
</pre>
</td>
<td>
<pre>
M/L=val-k/CA
payload : 
CA {
 m = <b>Nval-m</b>,
 n = <b>Nval-n</b>
}
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
a : val-a
b : val-b
g : <b>val-g1</b>
c : val-c
d : val-d
e : val-e
f : val-f
m : <b>val-m</b>
n : <b>val-n</b>
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
m : <b>Nval-m</b>
n : <b>Nval-n</b>
g : <b>val-g</b> (reset default)
</pre>
</td>
<td>
<pre>  
Existing behaviour
</pre>
</td>
</tr>
</pre>

<td>
<pre>
3. URI target is non-terminal
  container. Contents of  
  container and its nested 
  child containers map to
  separate tables.
<pre>
</td>
<td>
<pre>
/M/L[] { table-X  
 keys: k
 CA {
  leaves:m,n 
   C1 {
    leaves:a,b,g(def)      
    C2 { table-Y, key-Y
     leaves: c,d
     C3 { Table-Z, Key-Z
      leaves: e,f
     }
   }
  }
 }
}
</pre>
</td>
<td>
<pre>
/M/L=val-k/CA
payload : 
CA{
 C1 {
  a = <b>Nval-a</b>,
  b = <b>Nval-b</b>
 }
}
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
a : <b>val-a</b>
b : <b>val-b</b>
g : <b>val-g1</b>
m: val-m
n: val-n
--------------
table-Y|val-y
------------- 
c : val-c
d : val-d
-------------
table-Z|val-z
------------- 
e : val-e
f : val-f
  
</pre>
</td>
<td>
<pre>
table-X|val-k
------------- 
a : <b>Nval-a</b>
b : <b>Nval-b</b>
g : <b>val-g</b> (reset default)
-------------
<del>
table-Y|val-y
------------- 
c : val-c
d : val-d
-------------
table-Z|val-z
------------- 
e : val-e
f : val-f
</del>
</pre>
</td>
<td>
<pre>
The URI points to container CA with 
a parent instance val-k of L. If the
entries of table-Y and table-Z has
a relation to a parent instance,
i.e. table-X, those relevant
entries will be removed 
<b>Note:</b> Other entries of table-Y 
and table-Z will remain intact.
If the table ownership
is shared with other YANG nodes, 
update the entry instead by
removing only relevant fields.
</pre>  
</td>
</tr>
</pre>

<td>
<pre>
4. URI target is a complex
node having a child list, only
relevant instances of child list
will be wiped off. child containers
/lists map to separate table.
<pre>
</td>
<td>
<pre>
/M/L[] { table-X  
 keys: k
 CA {
  leaves:a,b,c,d
   C1 { table-Y, key-Y
    leaves:e,f,g(def)      
   L1[] { table-Z
    keys: z
    CZ { Table-Z, Key-Z
      leaves: m,n
     }
   }
  }
 }
}
</pre>
</td>
<td>
<pre>
/M/L=val-k1/CA
payload : 
CA{
  a = <b>Nval-a</b>,
  b = <b>Nval-b</b>
}
</pre>
</td>

<td>
<pre>
table-X|val-k1
------------- 
a : <b>val-a</b>
b : <b>val-b</b>
c : val-c
d : val-d
------------
table-X|val-k2
------------- 
a : val-a
b : val-b
--------------
table-Y|val-y
------------- 
e : val-e
f : val-f
g : val-g
-------------
table-Z|val-k1|key-z1
------------- 
m : val-m
n : val-n
-------------
table-Z|val-k1|key-z2
------------- 
m : val-m
n : val-n
-----------
table-Z|val-k2|key-z2
------------- 
m : val-m
n : val-n
</pre>
</td>

  
<td>
<pre>
table-X|val-k1
------------- 
a : <b>Nval-a</b>
b : <b>Nval-b</b>
------------
table-X|val-k2
------------- 
a : val-a
b : val-b
--------------
<del>  
table-Y|val-y
------------- 
e : val-e
f : val-f
g : val-g
-------------
table-Z|val-k1|key-z1
------------- 
m : val-m
n : val-n 
-------------
table-Z|val-k1|key-z2
------------- 
m : val-m
n : val-n
-----------
</del>
table-Z|val-k2|key-z2
------------- 
m : val-m
n : val-n
</pre>
</td>

<td>
<pre>
Entries of L1 related to L=val-k1
instance retrieved from traversal
will be removed.
</pre>  
</td>
</tr>
</pre>

<td>
<pre>
5. URI target is list and its
descendent child list node has
subtree annotated.
During traversal to child nodes of
target to identify tables to be
wiped off, subtree will be
invoked only for parent-list
instances not in payload.
<pre>
</td>
<td>
<pre>
/M/L[] { table-X  
 keys: k
 CA {
  leaves:m,n
   C1 {
    leaves:a,b
   }
   L1[] { xfmr_subtree handling table-Z|key-X|key-Z*
    keys: z
    CZ {
      leaves: x,y
     }
   }
  }
 }
</pre>
</td>
<td>
<pre>
payload : 
M/L   
payload : L {
  [
   key : val-k1
    CA {
     C1 { 
      a : val-a,
      b: val-b
     }
     L1 { 
      key : z1
      CZ { 
       x: val-x
      }
    }
  }
]
}
</pre>
</td>

<td>
<pre>
table-X|val-k1
------------- 
a : val-a
b : val-b
m : val-m
n : val-n
------------
table-X|val-k2
------------- 
a : val-a
b : val-b
m : val-m
n:  val-n
--------------
Subtree table data
table-Z|val-k1|key-z1
------------- 
x : val-x
y : val-y
-------------
table-Z|val-k1|key-z2
------------- 
x : val-x
y : val-y
-------------
table-Z|val-k1|key-z2
------------- 
x : val-x
y : val-y
-----------
table-Z|val-k2|key-z2
------------- 
x : val-x
y : val-y
</pre>
</td>

  
<td>
<pre>
table-X|val-k1
------------- 
a : val-a
b : val-b
<del>  
m : val-m
n : val-n
</del>  
------------
<del>
table-X|val-k2
------------- 
a : val-a
b : val-b
m : val-m
n: val-n
</del>  
--------------
Subtree table data
table-Z|val-k1|key-z1
------------- 
x : val-x
<del>  
y : val-y
</del>
-------------
<del>  
table-Z|val-k1|key-z2
------------- 
x : val-x
y : val-y
-------------
table-Z|val-k2|key-z2
------------- 
x : val-x
y : val-y
</del>  
</pre>
</td>

<td>
<pre>
Entries of L1 not in payload and
related to L=val-k1 instance, should be
deleted by subtree. Subtree should
fill this in subOpmap DELETE during
REPLACE flow. (Existing behaviour)
In order for the table-instances
to be marked for DELETE that are
not present in REPLACE payload,
Infra will invoke subtree L1 only
for L=val-k2 instance since its
not in payload and is retrievable
by infra.
</pre>  
</td>
</tr>

<td>
<pre>
6. URI target final node is
list instance and the table-instance
it maps to doesn't exist in DB.
Target list instance and payload
belong to separate tables.
<pre>
</td>
<td>
<pre>
list-X[] {
 keys:abc  
 containerA {
  list-A[] { Table-A
   keys:x
   config {
    u,v,w(def)
   }
   container-A1 { 
    list-A1[] { Table-A1
     keys:y
     cont-A11 {
       e, f, g
     }
    }
   }
   conatiner-A2 {
    list-A2[] { Table A2
      keys:z 
      contaA21 {
        q ,r
      }
    }
   }
  }
 }
}
</pre>
</td>
<td>
<pre>
/listX[abc]/contA/list-A[x]
payload: listA
{  val-x
  config {
    u,v
   }
  contA2
    list-A2[]
      val-z
      cont-A21 {
       leaf q
     }
}
</pre>
</td>

<td>
<pre>

Table-A|val-x DOES NOT exist

Table-A2|val-z  DOES NOT exist
</pre>
</td>

<td>
<pre>
Table-A|val-x
  u
  v
  w(def)

Table-A2|val-z
  q

</pre>
</td>

<td>
<pre>
*Instance created with NULL/NULL 
  if no leaf present in payload
*Instance created for target URI
final node IFF its a list instance
</pre>  
</td>
</tr>

<td>
<pre>
7. Target is at a yang node at a
  higher depth in yang and the
  child hierachy spans multiple
  tables mapped to child list
  and containers with and without
  defaults
<pre>
</td>
<td>
<pre>
cont-A {
  cont-X { TBL-X|keyX table-owner-false
      leaf-a
      leaf-b (default)
  }
  cont-Y { TBL-Y|keyY
      leaf-c
      leaf-d (default)
  }
  cont-C {
    list-C1 { TBL-C1|val-k
     keys :leaf-k
     cont-C1A
        leaf-k
        leaf-e
        leaf-f	
     }
     cont-C1B { TBL-C1B|keyC1B
         leaf-r
         leaf-s (default)
     }
     cont-C1D { TBL-C1D|keyC1D
          leaf-g
          leaf-h
          cont-C1D1 { TBL-C1D1|keyC1D1
              leaf-t
              leaf-u (default)
          }
     }
     cont-C1E {
       list-C1E1 {
         keys:leaf-q TBL-C1E1|val-q
         cont-D {
           leaf-q
           leaf-m
         }
         cont-E {
           leaf-n
           leaf-o (default)
         }
       }
     }
   }
  }
</pre>
</td>
<td>
<pre>
PUT target: /cont-A
payload:
cont-A {
  cont-C {
    list-C1[] {
      key : val-k1
      cont-C1A {
        k1
      }
      cont-C1D {
        cont-C1D1 {
          t
        }
      }
      cont-C1E {
        list-C1E1[] {
          key : val-q
          cont-D {
            q
          }
        }
      }
    }
  }
}
</pre>
</td>

<td>
<pre>
DB contents before
TBL-X|keyX
------------------
  leaf-a: vala
  leaf-b: valb
  leaf-ww: valww
  leaf-vv: valvv
Tbl-Y|keyY
------------------
  leaf-c: valc
  leaf-d: vald
TBL-C1|val-k1
------------------
  leaf-e: vale
</pre>
</td>

<td>
<pre>
DB contents after
TBL-X|keyX
------------------  
  <del>  
  leaf-a: vala
  leaf-b: valb (default)
  </del>  
  leaf-ww: valww
  leaf-vv: valvv
<del>  
Tbl-Y|keyY
------------------  
  leaf-c: valc
  leaf-d: vald (default)
</del>
TBL-C1|val-k1
------------------         
  NULL: NULL
TBL-C1D1|keyC1D1
------------------         
  leaf-t: valt
  leaf-u: valu (default)
TBL-C1E1|val-q
------------------         
  leaf-o: valo (default)
  
</pre>
</td>

<td>
<pre>
*Instances C1B mapping to a container
and having a default will not be created 
since its not in the payload.
*Instance C1D mapping to a container
not having any default and no data
in the payload for it, will not be created.
</pre>  
</td>
</tr>

</tr>
</pre>
</table>


# 5 Yang annotation and callback considerations for feature apps

GET like yang tree traversal for north bound DELETE operation will be introduced in order to identify all the relevant child tables/instances to be deleted for the request URI. 
As part of the REPLACE/PUT support, infra will leverage this GET like traversal for the DELETE flow in order to identify all the relevant child tables/instances to be deleted for the request URI and are not part of the REPLACE payload.
Application owners will need to have appropriate annotations and logic in the callbacks to facilitate the GET like yang hierarchy traversal for DELETE and also process PUT payload appropriately.Following are the annotation and callback considerations for feature apps:

**1. Shared table ownership handling**

This annotation will be useful in cases where DB table has data not only from the mapped yang node in the request, but also from host or another yang and a REPLACE/DELETE operation should not act on the whole instance but just a subset of fields.

**Static annotation**

- Use the **table-owner:false** annotation where there is table-annotation(table-name/table-xfmr) and the openconfig yang node doesn't own that mapped table. 
- By default table-ownership is always true so annotate only when false/non-table owner.
- In case of table-xfmr, whatever table it returns is never owned by the yang then use static table-owner:false annotation.

**Dynamic annotation**

- If the table returned by table-xfmr is owned by the yang node for a given instance/key but for some other key it does not own the table then in such case set dynamic flag **\*isNotTblOwner** to true and don't use static annotation. When returning a single table as per the key in URI, the dynamic flag can be filled by the table-xfmr callback.
- when multiple tables are returned by the table-xfmr for URI targeted at whole list then do not set the flag for table-owner becuase infra will process every instance for every table, and to traverse the child yang hierarchy the table xfmr will be invoked per instance again that will map to single table.

**Note:** Do not mix static table-owner annotation with dynamic, a static table-owner annotation will take precedence.

**Not having appropriate table-owner annotation indicating shared ownership will result in deletion/modification of complete table-instance** deleting the fields not owned by the mapped yang node.

Refer example below :

```golang
// e.g. STATIC ANNOTATION table-owner:false
module: openconfig-system
  +--rw system 
     +--rw config #annot# key-transformer:sys_config_key_xfmr table-name:DEVICE_METADATA table-owner:false
     |  +--rw hostname?                      string
     |  +--rw oc-sys-dev:intf-naming-mode?   intf-mode #annot# field-transformer:intf_naming_mode_xfmr field-name:intf_naming_mode
. . .
     +--rw clock #annot# table-name:CLOCK key-transformer:system_clock_key_xfmr
     |  +--rw config
     . . .
. . .
     +--rw dns
     |  +--rw config #annot# table-name:DNS key-transformer:global_dns_key_xfmr
     . . .
. . .
     |  +--rw servers #annot# table-name:NONE
     . . .
 
// e.g. DYNAMIC table-owner identification in table transformer using inParams.isNotTblOwner
module: openconfig-test
+--rw test #annot# user-role-priv:write:netadmin
+--rw interfaces
| +--rw interface* [interface-id] #annot# key-transformer:test_intf_tbl_key_xfmr table-transformer:test_intf_table_xfmr 
| +--rw interface-id -> ../config/interface-id #annot# field-transformer:test_intf_intf_id_fld_xfmr
| +--rw config
| | +--rw interface-id? string #annot# field-transformer:test_intf_intf_id_fld_xfmr
| +--ro state
| | +--ro interface-id? string #annot# field-transformer:test_intf_intf_id_fld_xfmr
 
var test_intf_table_xfmr TableXfmrFunc = func(inParams XfmrParams) ([]string, error) {
    var tblList []string
    var key string
 
    pathInfo := NewPathInfo(inParams.uri)
    targetUriPath := pathInfo.YangPath
    ifName := pathInfo.Var("interface-id")
     
    tbl_name := ""
    if len(ifName) != 0 {
        key = ifName
         
        if utils.IsIntfSubInterface(dbifName) {
            tbl_name = "TABLE_A"
            if inParams.isNotTableOwner != nil {
                *inParams.isNotTableOwner = true // Non table owner case. Set dynamic table ownership here
            } 
        } else if strings.HasPrefix(*dbifName, "Eth") {
            tbl_name = "TABLE_B"
            if inParams.isNotTableOwner != nil {
                *inParams.isNotTableOwner = true // Non table owner case. Set dynamic table ownership here
            }
        } else if strings.HasPrefix(*dbifName, "Vlan") {
            tbl_name = "TABLE_C"  // Table owner case
        } else if strings.HasPrefix(*dbifName, "PortChannel") {
            tbl_name = "TABLE_D" // Table owner case
        } else {
            log.Info("qos_intf_table_xfmr - Invalid interface type")
            return tblList, errors.New("Invalid interface type")
        }
        tblList = append(tblList, tbl_name)
   } else {
     // URI targeting whole list case
     tblList = append(tblList, "TABLE_A", "TABLE_B", "TABLE_C", "TABLE_D")
   }
   return tblList
}
```

______________________________________________________________________________________
**2. Table transformer handling for virtual table case**

GET like traversal of the yang hierarchy beneath the target URI to identify the tables/instances to be deleted for both north bound DELETE and PUT operation will be done by infra which needs to be faciltatate by application table transformer callbacks for virtual table cases identified by virtual table annotation.This annotation indicates that there is no DB mapping to the corresponding yang node but that yang node still has to be traversed to reach the child hierarchy.

**Static annotation (existing annotation)**

Use the **virtual-table:true** annotation where there is table-xfmr annotation and the yang node doesn't map to any real DB table but the node needs to traversed to the reach child yang hierarchy wher DB mappings exist.
By default all tables identified at a yang node are considered as mapped to real DB table (virtual-table:false)

**Dynamic annotation (existing annotation)**

If a table returned by table-xfmr for a given key in URI maps to a real DB table but for another given key it doesn't map to a DB table then in such case set dynamic flag  ***inParams.isVirtualTbl = true** and don't use static annotation. 
When the table xfmr returns a single table as per the key in URI, the dynamic flag for  virtual table can be filled by the callback.When multiple tables are returned by the table-xfmr for URI targeted at whole list then do not set the flag becuase infra will process every instance in every table and the table xfmr will be invoked again per instance that will map to single table.

**Note:** Do not mix static  annotation with dynamic, a static annotation will take precedence.

Refer example below :
 ```golang
 // Example logic in table-xfmr mapped to virtual table to fill only relevant instances in dbDataMap to aid traversal of child nodes in yang hierarchy.
module: openconfig-network-protocols
  +--rw network-instances
     +--rw network-instance* [name] #annot# table-transformer:network_instance_table_name_xfmr key-transformer:network_instance_table_key_xfmr
        +--rw name
        +--rw protocols #annot# table-name:NONE
        |  +--rw protocol* [identifier name] #annot# virtual-table:true table-transformer:network_instance_protocols_ptotocol_table_name_xfmr key-transformer:network_instance_protocol_key_xfmr
        |     +--rw identifier                            -> ../config/identifier
        |     +--rw config
        |     |  +--rw identifier?   identityref
        |     +--ro state
        |     |  +--ro identifier?   identityref
        ...
        |     +--rw bgp #annot# table-transformer:bgp_tbl_xfmr key-transformer:protocol1_key_xfmr validate-xfmr:bgp_validate_proto
        |     |  +--rw global
        ...
        |     +--rw ospfv2 #annot# validate-xfmr:ospfv2_validate_proto
        |     |  +--rw global
        ...
        |     +--rw pim #annot# validate-xfmr:pim_validate_proto
        |     |  +--rw global
        ...
         
var network_instance_protocols_ptotocol_table_name_xfmr TableXfmrFunc = func(inParams XfmrParams) ([]string, error) {
        var tblList []string
 
        log.V(3).Info("network_instance_protocols_protocol_table_name_xfmr")
        if inParams.oper == GET || inParams.oper == DELETE {
                pathInfo := NewPathInfo(inParams.uri)
                niName := pathInfo.Var("name")
                protoId := pathInfo.Var("identifier")
                protoNm := pathInfo.Var("name#2")
                cfg_tbl_updated := false
                if inParams.dbDataMap != nil {
                        if (niName == "default") || (strings.HasPrefix(niName, "Vrf")) {
                                (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"] = make(map[string]db.Value)
                                cfg_tbl_updated = true
                                if protoId == "" { // inParams.uri at whole list level, hence add all child instances to be traversed
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["BGP|bgp"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["BGP|bgp"].Field["NULL"] = "NULL"
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["OSPF|ospfv2"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["OSPF|ospfv2"].Field["NULL"] = "NULL"
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["PIM|pim"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["PIM|pim"].Field["NULL"] = "NULL"
                                        ...
                                } else if protoId != "" && protoNm != "" {
                                    if protoId == "BGP" && protoNm == "bgp" {
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["BGP|bgp"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["BGP|bgp"].Field["NULL"] = "NULL"
                                        cfg_tbl_updated = true
                                    }
                                    if protoId == "OSPF" && protoNm == "ospfv2" {
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["OSPF|ospfv2"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["OSPF|ospfv2"].Field["NULL"] = "NULL"
                                        cfg_tbl_updated = true
                                    }
                                    if protoId == "PIM" && protoNm == "pim" {
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["PIM|pim"] = db.Value{Field: make(map[string]string)}
                                        (*inParams.dbDataMap)[db.ConfigDB]["CFG_PROTO_TBL"]["PIM|pim"].Field["NULL"] = "NULL"
                                        cfg_tbl_updated = true
                                    }
                                    ...
                                }
                        } else {
                            // Add appropriate tables based on niName and protoId
                        }
                        if cfg_tbl_updated {
                                tblList = append(tblList, "CFG_PROTO_TBL")
                        }
                }
        } else {
            // Since it is marked as static virtual table in annotations, return empty table list fort SET cases (CRU)
        }
        return tblList, nil
}      
 
// The validate transformer function shall be annotated for all nodes that have a relevant mapping based on conditions (when statements in yang) like the parent list key etc.
func bgp_validate_proto(inParams XfmrParams) bool {
    pathInfo := NewPathInfo(inParams.uri)
    id := pathInfo.Var("identifier")
    name := pathInfo.Var("name#2")
    if id == "BGP" && name == "bgp" {
        return true
    }
    return false
}
```

______________________________________________________________________________________
**3. Key transformer handling for whole list case**

In order to aid GET like traversal of the yang hierarchy beneath the target URI to identify the tables/instances to be deleted for both north bound DELETE and PUT operation,
when a key-transformer is invoked at **whole list level** and the Db-key at this list **uses parent key** then the key-transformer should **return partial-key** for infra to process only the relevant instances.If there is no relation to parent key then an empty key can be returned so that all table instances will be processed by infra.
If partial-key not returned then infra ends up processing all instances to decide which ones to filter out impacting performance.
Please Note the key transformer will have to return the exact key if the xfmr function is invoked for the list instance (URI having keys).

Refer below example:
```golang
 When we do a DELETE at rdnss-addresses container, only those instances of the rdnss-address list will have to be traversed that are relevant for the parent interface list instance in the request.Here the key-transformer should return partial-key that belongs to interface parent list to retrieve and delete only the relevant rdnss-addresses 

        |        |  +--rw oc-intf-ext:rdnss-addresses
        |        |  |  +--rw oc-intf-ext:rdnss-address* [address] #annot# key-transformer:nd_eth_rdnss_key_xfmr table-name:ND_RDNSS
        |        |  |     +--rw oc-intf-ext:address    -> ../config/address
        |        |  |     +--rw oc-intf-ext:config
        |        |  |     |  +--rw oc-intf-ext:address?          oc-inet:ipv6-address #annot# field-name:address field-transformer:nd_eth_rdnss_address_fld_xfmr
        |        |  |     |  +--rw oc-intf-ext:valid-lifetime?   uint32
        |        |  |     +--ro oc-intf-ext:state
        |        |  |        +--ro oc-intf-ext:address?          oc-inet:ipv6-address
        |        |  |        +--ro oc-intf-ext:valid-lifetime?   uint32  
           
 
        // Annotation
        deviation /oc-intf:interfaces/oc-intf:interface/oc-intf:subinterfaces/oc-intf:subinterface/oc-ip:ipv6/oc-ip:router-advertisement/oc-intf-ext:rdnss-addresses/oc-intf-ext:rdnss-address {
          deviate add {
            sonic-ext:key-transformer "nd_eth_rdnss_key_xfmr";
            sonic-ext:table-name "ND_RDNSS";
          }
        }
             
    var YangToDb_nd_eth_rdnss_key_xfmr KeyXfmrYangToDb = func(inParams XfmrParams) (string, error) {
        var neightbl_key string
        var err error
 
        log.Info("YangToDb_nd_eth_rdnss_key_xfmr - inParams: ", inParams)
        pathInfo := NewPathInfo(inParams.uri)
 
        rcvdIfName, ifName, subIdxStr, subIdx, ifNameInDb, keyname, err1 := ndGetifNameFrmPathInfo(*pathInfo)
        log.Infof("YangToDb_nd_eth_rdnss_key_xfmr : RcvdName: %s, NativeName: %s, subIdxStr: %s, subIdx: %d, ifNameInDb: %s, keyname: %s, err1: %s", rcvdIfName, ifName, subIdxStr, subIdx, ifNameInDb, keyname, err1)
 
        log.Info("YangToDb_nd_eth_rdnss_key_xfmr : pathInfo ", pathInfo)
        log.Info("YangToDb_nd_eth_rdnss_key_xfmr : inParams.uri ", inParams.uri)
 
        ...

        ipv6Addr := pathInfo.Var("address")
        if len(ipv6Addr) <= 0 {
                log.Infof("YangToDb_nd_eth_rdnss_key_xfmr - IPv6 Address not found, returning NativeName %s", ifName)
                return ifName, err  // whole-list case , return only parent key
        }
        neightbl_key = keyname + "|" + ipv6Addr
        log.Info("YangToDb_nd_eth_rdnss_key_xfmr - key returned: ", neightbl_key)
 
        return neightbl_key, err
}
```

______________________________________________________________________________________
**4. Validate transformer annotation (formerly get-validate) extended to CRUD**

Validate-xfmr should be annotated if a yang node need not be traversed when traversal is being done from a specific parent.
Current **annotation of "get-validate" will be changed to "validate-xfmr"** so that it can be used for CRUD cases as well as GET.

Application validate transformer callbacks should be annotated at appropriate nodes and accommodate for all operations else infra might end up processing invalid nodes resulting in incorrect final result or performance impact.

See the above example of bgp_validate_proto() in point 2 above.

**5. Subtree - populate DB data under appropriate operation (No changes to subtree invocation by transformer infra)**

Guideline on how subtree should handle PUT payload:

- If subtree has complete table-instance ownership then it should translate the payload into the result explicitly returned by subtree. This the result of incoming operation/PUT.
- If subtree doesn't own the table then it should fill subOpDataMap[UPDATE] with fields in payload, and fields not in payload for the node in request into the subOpDataMap[DELETE].
- In spite of complete table-instance ownership, if the north bound request URI is such that it spans only a subset of fields in table-instance then populate the payload fields into  subOpDataMap[UPDATE]                                                                                              and fields not in payload for the node in request into the subOpDataMap[DELETE].
- Subtree should also identify instances to be deleted, that it handles but are not in request payload and are relevant to the parent instance in the request. Add them to the
subOpDataMap[DELETE]. If subtree doesn't own the table-instance then it should add all relevant fields for such instances.
- **Considerations should be made as below.** (for both complete ownership and shared ownership with resources).
   - Examine the north-bound request URI (could be at any - parent level, at subtree node level or child node level of the subtree annotated node) and decide the transformation operation based on the DB table mapping, table-ownership etc.
   - Identify instances to be deleted, handled by the subtree that are not in request payload and are relevant to the parent instance in the request. Add them to the subOpDataMap[DELETE].
   - Any other transformation required by the subtree can be filled into subOpDataMap(map for other operations) with the appropriate DB changes required as per the application need.
   - Subtree invoked for first time when processing payload per unique instance from parent hierarchy, it is recommended that subtree processes the entire ygot under this subtree and set the
     **inParams.invokeCRUSubtreeOnce=true** flag so that subtree is invoked only once giving performance improvement.

   Refer example below:

  ```golang
   // e.g.module: openconfig-xyz-tree
  +--rw xyz
     +--rw mstp
     |  |  ...
     |  +--rw mst-instances
     |     +--rw mst-instance* [mst-id]
     |        +--rw mst-id        -> ../config/mst-id
     |        +--rw config
     |        |  +--rw mst-id?           
     |        +--ro state
     |        .....
     |        +--rw interfaces    #annot# subtree-transformer:xyz_mst_intf_xfmr
     |           +--rw interface* [name]
     |              +--rw name      -> ../config/name
     |              +--rw config
     |              |  +--rw name?           
     |              |  +--rw a?           
     |              |  +--rw b?  
     |              +--rw def
     |                 +--rw config
     |                 | +--rw c?          
     |                 | +--rw d?          
     |                 +--ro state
     |                 +...
 
 
    var YangToDb_xyz_mst_intf_xfmr SubTreeXfmrYangToDb = func(inParams XfmrParams) (map[string]map[string]db.Value, error) {
        var err error
        resMap := make(map[string]map[string]db.Value)
        xyzMstPortMap := make(map[string]string)
        subOpMap := make(map[db.DBNum]map[string]map[string]db.Value)
        reqXpath, _, xpathErr = XfmrRemoveXPATHPredicates(inParams.requestUri) //URI with which North Bound request is made
        pathInfo := NewPathInfo(inParams.uri) //URI with which infra calls subtree while processing payload
        mstInstName := pathInfo.Var("mst-id")
        ifName := pathInfo.Var("name")
 
        /*REPLACE and DELETE handling*/
        if strings.HasPrefix(reqXpath, "openconfig-xyz-tree:xyz/mstp/mst-instances/mst-instance/interfaces/interface/config") {
                if inParams.oper == REPLACE {
                        /* Extract leaf values from YGOT and fill into inParams.subOpDataMap[UPDATE] since the request target is
                           container covering only subset fields in table
                         */
                        subOpMap[XYZ_MST_PORT_TABLE] = make(map[string]db.Value)
                        xyzMstPortKey := mstInstName + "|" + ifName
                        xyzMstPortMap["a"] = <valueFromYgot>
                        xyzMstPortMap["b"] = <valueFromYgot>
                        subOpMap[STP_MST_PORT_TABLE][xyzMstPortKey] = db.Value{Field: xyzMstPortMap}
                        inParams.subOpDataMap[UPDATE] = &subOpMap
                } else if inParams.oper == DELETE {
                        /*Fill appropriate leaf data into result that is being returned for inParams.oper i.e. resMap*/
                        if reqXpath == "openconfig-xyz-tree:xyz/mstp/mst-instances/mst-instance/interfaces/interface/config" {
                                /* Fill all leaves under interface/container with blank values in resMap*/
                        } else {
                                /* Fill the leaf for which the North bound request is made in resMap */
                        }
                }
        } else if strings.HasPrefix(reqXpath, "openconfig-xyz-tree:xyz/mstp/mst-instances/mst-instance/interfaces/interface/def") {
                /* For REPLACE and DELETE same handling as above case of interface/config level */
        } else if strings.HasPrefix(reqXpath, "openconfig-xyz-tree:xyz/mstp/mst-instances/mst-instance/interfaces/interface") && strings.HasSuffix(inParams.requestUri, "]") {
                /* North bound request is for specific interface instance */
                if inParams.oper == REPLACE {
                   /* Extract leaf values from YGOT and fill into result that is being returned for inParams.oper i.e. resMap. This is in case where subtree owns the table.
                      For table not owned by subtree fill the leaves in payload into subOpMap[UPDATE] and leaves not in payload into subOpMap[DELETE] */
                } else if  inParams.oper == DELETE {
                   /* For DELETE oper fill the instance to be deleted into result that is being returned for inParams.oper i.e. resMap. Since its instance level DELETE NO leaves/fields to be filled
                      This in case where subtree owns the table. If subtree doesn't own then fill all the relevant yang leaves into subOpMap[DELETE].*/
               } 
        } else { /* North bound request at any level from top level container(xyz) to list(interface without instance)*/
               subtreeCallAtXpath, _, xpathErr := XfmrRemoveXPATHPredicates(inParams.uri)
 
               /* subtree invoked for first time when processing payload per <mstInstName>/parent.It is recommended that subtree processes the entire ygot under subtree per mstInstName/parent and set the
                  inParams.invokeCRUSubtreeOnce flag to true so that subtree is invoked only once giving performance improvement */
               if strings.HasPrefix(subtreeCallAtXpath, "openconfig-xyz-tree:xyz/mstp/mst-instances/mst-instance/interfaces") { // prefix points to yang node at which subtree is annotated
                   if inParams.oper == REPLACE {
                        /* For the mstInstName(parent-yang-key for which subtree was called) range through each interface instance in YGOT to extract the leaves and fill into
                           result that is being returned for inParams.oper/REPLACE i.e. resMap.This is in case where subtree owns tables.For tables that are not owned by subtree fill the leaves in payload
                           into subOpMap[UPDATE] and leaves NOT in payload into subOpMap[DELETE].
                           Fetch all interface instances from DB matching parent-yang-key pattern "<mstInstName>|*" and range through
                           them to filter out that are NOT present in incoming ygot and then add them to inParams.subOpDataMap[DELETE].This is in case where subtree owns tables.
                           If subtree doesn't own then fill all the relevant yang leaves into subOpMap[DELETE] for all "<mstInstName>|*" interface instances existing in DB but NOT in payload.
                         */
                   } else if inParams.oper == DELETE {
                        /* Fetch all interface instances from DB matching pattern "<mstInstName>|*"(parent-yang-key for which subtree was called) and add them to
                        result that is being returned for inParams.oper i.e. resMap.This in case where subtree owns tables.
                        If subtree doesn't own then fill all the relevant yang leaves into subOpMap[DELETE] for the  "<mstInstName>|* interface instances retrieved above. */
                   }
                }
        }
        log.Info("YangToDb_xyz_mst_intf_xfmr resMap: ", resMap)
        return resMap, err
   }
   ```

______________________________________________________________________________________
**6.Post transformer**

The post-xfmr can be used for cases that are very application specific and does not conform to the REPLACE / DELETE behavior. 

Usage of post-transformer for extensive changes in final result map is not recommended and should be used for exceptional cases where the application can look at the infra generated inParams.dbDataMap and inParams.subOpDataMap and modify if required.
______________________________________________________________________________________
**Note:** 
  CVL validations that are in place for DB tables resulting from performing an operation at any yang depth will continue to be exercised when performing DB operations and will be factor in deciding the final outcome.

# 6 Unit Tests

>  In order to exercise transformer infrastructure model based REPLACE & DELETE flow, following unit test cases require application annotation and callbacks to have appropriate logic to aid in GET like yang tree traversal producing intended result.
  Test YANG will be used to simulate these conditions.Each test shall cover value REPLACE and DELETE cases wherever possible.
  - PUT request URI targeted at whole list with payload containing multiple instances, some of which are present in DB and some not, should result in - a) replacing/swapping the instances already existing in DB with new contents from request payload, b) deleting instances present in DB but not in request payload and c) creating the instances not present in DB.
  - PUT request URI targeted at container spanning only subset of attributes/fields in the mapped table-entry should update the attributes present in payload and delete the attributes not present in payload for the targeted container, except resetting the ones having yang defaults, keeping other attributes in the DB table instance intact.
  - PUT payload containing instances mapped with table-owner false annotation should not result in swapping the whole table-entry with new payload keeping the other attributes in the table-entry, that are not mapped in the request yang intact.
  - PUT request URI targeted at list instance not present in DB should create the instance with attributes from payload.
  - PUT request URI targeted at leaf/leaf-list node should update the value with new value in payload.
  - DELETE request URI targeted at whole list/list-instance should delete all list instances/targeted list-instance respectively,that exist in DB, including the relevant insances in the child yang hierarchy.In case of non table-owner only the attributes in the yang hierarchy should be deleted.Yang nodes in the child yang hierarchy having virtual table mapping should not be marked for delete.
  - DELETE request URI targeted at container should delete only the attributes under that container.Child yang hierachy should be traversed and relevant instances should be deleted.Yang nodes in the child yang hierarchy having virtual table mapping should not be marked for delete.
  - DELETE request targeted at leaf node should delete the corresponding DB attribute in mapped table-entry.If leaf has yang default it should reset to default.
  - DELETE request targeted at leaf-list instance should delete the specific instance and if the request is targeted at entire leaf-list then the corresponding attribute in table-entry should get deleted.