

# REST Query Parameter Support for GET requests

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
| Rev  |    Date    |            Author            | Change Description     |
| :--: | :--------: | :--------------------------: | ---------------------- |
| 0.1  | 04/15/2021 | Kwan, Amruta, Ranjini & Mari | Initial version        |
| 0.2  | 07/08/2021 |             Kwan             | Update the section 2.2 |

# About this Manual
This document provides general information about the REST Query Parameter Support for GET requests served through management framework.

# Scope
This document describes the high-level design of depth, content and fields REST query parameters for GET request only. 
•	List is not supported in FIELDS QP(i.e. fields-expr).
•	GNMI extension for the REST-like query parameter is not covered now. It can be supported as the registered extension if needed, in the future. 
•	Event stream filter is not supported.


# Definition/Abbreviation

### Table 1: Abbreviations
| **Term** | **Meaning**                     |
| -------- | ------------------------------- |
| QP       | Query parameter                 |
| REST     | Representational State Transfer |

# 1 Feature Overview

RESTCONF operation allows zero or more query parameters to be present in the request URI.  QP can be used as a complementary option to allow the user to query for selected data of their interest. Management infra will provide support the following QPs for GET request
•	Depth
•	Content
•	Fields
QP support will be enabled for open-config yang, sonic yang and ietf yang models. 

## 1.1 Requirements

Requirement to support query parameters for GET request only. Note that the QP related to event streams – filter, start-time and stop-time, is not covered in this HLD.

### 1.1.1 Functional Requirements

** **

| **Sr No.** | **Requirement**                          | **Comments**                             |
| ---------- | ---------------------------------------- | ---------------------------------------- |
| 1          | Each RESTCONF [RFC8040]  operation allows zero or more query parameters to be present in the request  URI. The specific parameters that are allowed depends on the resource type,  and sometimes the specific target resource used, in the request. | Only for GET request.                    |
| 2          | Query parameters can be  given in any order. Each parameter can appear at most once in a request URI. |                                          |
| 3          | Support **DEPTH** based  query parameter. The value of the "depth" parameter is either an  integer between 1 and 65535 or the string "unbounded".  "unbounded" is the default |                                          |
| 4          | Support **CONTENT**  based query parameter. Content can be “all” or “config” or “non-config”.  Default is “all”. | GNMI: operational –  data in “non-config” & not in “config”. |
| 5          | Support **FIELDS**  based query parameter to retrieve a subset of all nodes in a target resource.  Single or multiple fields can be specified in the “field” query parameter. | Field query parameter  support is limited to cases listed in **"Field based QP requirements" ** table. |

Refer following RFC links for detailed description and examples on Depth, Content and Fields query parameters.
Depth Query Parameter:
​	https://tools.ietf.org/html/rfc8040#section-4.8.2
​	https://tools.ietf.org/html/rfc8040#appendix-B.3.2 
Content Query Parameter:
​	https://tools.ietf.org/html/rfc8040#section-4.8.1
​	https://tools.ietf.org/html/rfc8040#appendix-B.3.1 
Fields Query Parameter:
​	https://tools.ietf.org/html/rfc8040#section-4.8.3 
​	https://tools.ietf.org/html/rfc8040#appendix-B.3.3

Fields QP will allow only the following parameter types:
<u>**Field based QP requirements**</u>

| Type                                     | Description                              | Query  Format                            |
| ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| Singe  field                             | Return  only data node, matching the field. | http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA=<keyValue-keyX>?fields=leaf1        <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA?fields=leaf1      <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB?fields=container-CC(leaf1) |
| Multiple  fields                         | Return  only data nodes, matching the fields | http://100.100.10.10/restconf/data/yang-module:container-CA/list-LA?fields=leaf1;leaf2;leaf3       <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA=<keyValue-keyX>?fields=container-CA  (leaf1;leaf2;leaf3) |
| fields at  current level & child container fields path | Return  data nodes matching the fields at current level and all descendant data  nodes, matching the fields inside child container/list path. | http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA?fields=leaf1;container-CC/leaf2      <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA?fields=leaf1;container-CC      <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA=<keyValue-keyX>/?fields=leaf1; container-CC/leaf2       <br />http://100.100.10.10/restconf/data/yang-module:container-CA  /container-CB/list-LA=<keyValue-keyX>/?fields=leaf1; container-CC |

### 1.1.2 Configuration and Management Requirements
Content, depth and field query parameters can be supplied in REST request URL of a GET request.

Eg. : curl -X GET "https://localhost/restconf/data /openconfig-network-instance:network-instances/networkinstance=default/protocols/protocol=IGMP_SNOOPING,IGMPSNOOPING/openconfig-network-instance-deviation:igmpsnooping?depth=4 " -H "accept: application/yang-data+json" -H "ContentType: application/yang-data+json" 

### 1.1.3 Scalability Requirements
Performance with QP should be better or equal to the current GET request performance without QP.

### 1.1.4 Warm Boot Requirements
N/A

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC management framework will be enhanced to enable QP support for GET request.

### 1.2.2 Container
Management framework.

### 1.2.3 SAI Overview
N/A

# 2 Functionality
## 2.1 Target Deployment Use Cases
This feature enables the users to query the system for specific data of interest.

## 2.2 Functional Description
###### **Depth support:**   (RFC 8040) 4.8.2. The "depth" Query Parameter

The "depth" query parameter is used to limit the depth of subtrees returned by the server. Data nodes with a "depth" value greater than the "depth" parameter are not returned in a response for a GET method. The requested data node has a depth level of "1". If the "fields" parameter (Section 4.8.3) is used to select descendant data nodes, then these nodes and all of their ancestor nodes have a "depth" value of "1". (This has the effect of including the nodes specified by the fields, even if the "depth" value is less than the actual depth level of the specified fields.) Any other child node has a "depth" value that is 1 greater than its parent. The value of the "depth" parameter is either an integer between 1 and 65535 or the string "unbounded". "unbounded" is the default. This parameter is only allowed for GET methods on API, datastore, and data resources. A "400 Bad Request" status-line is returned if used for other methods or resource types.

By default, the server will include all sub-resources within a retrieved resource that have the same resource type as the requested resource. The exception is the datastore resource. If this resource type is retrieved, then by default the datastore and all child data resources are returned. If the "depth" query parameter URI is listed in the "capability" leaf-list defined in Section 9.3, then the server supports the "depth" query parameter.

**                      **

| **Unbounded/depth=0 **                                       |
| ------------------------------------------------------------ |
| Request : curl -X GET "https://localhost/restconf/data/openconfig-network-instance:network-instances/networkinstance=default/protocols/protocol=IGMP_SNOOPING,IGMPSNOOPING/openconfig-network-instance-deviation:igmp-snooping?**depth=0**" -H "accept: application/yang-data+json" -H  "Content-Type: application/yang-data+json" |
| {<br/>	"openconfig-network-instance-deviation:igmpsnooping": {<br/>		"interfaces": {<br/>			"interface": [{<br/>				"config": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				},<br/>				"name": "Vlan1",<br/>				"state": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				}<br/>			}, {<br/>				"config": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				},<br/>				"name": "Vlan2",<br/>				"state": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				}<br/>			}]<br/>		}<br/>	}<br/>} |

| **depth=4 **                                                 |
| ------------------------------------------------------------ |
| Request: curl -X GET "https://localhost/restconf/data/openconfig-network-instance:network-instances/networkinstance=default/protocols/protocol=IGMP_SNOOPING,IGMPSNOOPING/openconfig-network-instance-deviation:igmpsnooping?**depth=4**"  -H "accept: application/yang-data+json" -H  "Content-Type: application/yang-data+json” |
| Response:  {    "openconfig-network-instance-deviation:igmpsnooping":    {<br />      "interfaces":  {<br />        "interface":  [{<br />          "name":  "Vlan1"<br />        }, {<br />         "name":  "Vlan2"<br />        }]<br />      }<br />    }<br />  } |

**Example: depth level of a node:** 

{
	"openconfig-networkinstancedeviation:igmpsnooping": { //d 4 "interfaces": { //d 3 "interface":[{ //d 2 ":igmpsnooping"
		"config": { //d 1
			"enabled": true, //d 0
			"lastmemberqueryinterval": 2000, //d 0
			"name": "Vlan1" //d 0
		},
		"name": "Vlan1", //d 1
		"state": { //d 1
			............... //d 0
			.............. //d 0
		}
	}



###### **Content Support:**    (RFC 8040) 4.8.1. The "content"Query Parameter

The"content" query parameter controls how descendant nodes of the requested data nodes will be processed in the reply. The allowed values are:

**Table5:**

| **Value**     | **Description**                                              |
| ------------- | ------------------------------------------------------------ |
| config        | Return  only configuration descendant data nodes             |
| non config    | Return  only non-configuration descendant data nodes         |
| *operational* | Return  only non-configuration descendant data nodes (**applicable only for OC yang -GNMI request** ) |
| all           | Return  all descendant data nodes                            |

This parameter is only allowed for GET methods on datastore and data resources. A "400 Bad Request" status-line is returned if used for other methods or resource types. If this query parameter is not present, the default value is"all". This query parameter MUST be supported by the server.
<u>Note:</u> "operational" content type is only applicable for GNMI request. This is currently supported for OC yang only and "400 Bad Request" error will be returned for other yang models.

| **content-type  = all**                                      |
| ------------------------------------------------------------ |
| *Request :*  curl -X GET "https://localhost/restconf/data/openconfig-networkinstance:network-instances/network-instance=default/protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING/openconfig-network-instance-deviation:igmp-snooping?**content=all**" -H "accept: application/yang-data+json" -H  "Content-Type: application/yang-data+json”<br /> |
| {<br/>	"openconfig-network-instance-deviation:igmpsnooping": {<br/>		"interfaces": {<br/>			"interface": [{<br/>				"config": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				},<br/>				"name": "Vlan1",<br/>				"state": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				}<br/>			}, {<br/>				"config": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				},<br/>				"name": "Vlan2",<br/>				"state": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				}<br/>			}]<br/>		}<br/>	}<br/>} |

| **content-type  = config**                                   |
| ------------------------------------------------------------ |
| *Request:*  curl -X GET "https://localhost/restconf/data/openconfig-networkinstance:network-instances/network-instance=default/protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING/openconfignetwork-instance-deviation:igmp-snooping?**content=config**" -H "accept: application/yang-data+json" -H  "Content-Type: application/yang-data+json”<br /> |
| {<br/>	"openconfig-network-instance-   deviation:igmpsnooping": {<br/>		"interfaces": {<br/>			"interface": [{<br/>				"config": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				},<br/>				"name": "Vlan1"<br/>			}, {<br/>				"config": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				},<br/>				"name": "Vlan2"<br/>			}]<br/>		}<br/>	}<br/>} |

| content-type  = non-config                                   |
| ------------------------------------------------------------ |
| *Request:*  curl -X GET "https://localhost/restconf/data/openconfig-networkinstance:network-instances/network-instance=default/protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING/openconfignetwork-instance-deviation:igmp-snooping?**content=nonconfig**"  -H "accept: application/yang-data+json" -H "Content-Type:  application/yang-data+json"     <br /><br /> |
| {<br/>	"openconfig-network-instance-deviation:igmpsnooping": {<br/>		"interfaces": {<br/>			"interface": [{				<br/>				"name": "Vlan1",				<br/>				"state": {					<br/>					"enabled": true,					<br/>					"last-memberquery-interval": 2000,					<br/>					"name": "Vlan1"<br/>				}<br/>			}, {				<br/>				"name": "Vlan2",				<br/>				"state": {					<br/>					"enabled": false,					<br/>					"last-memberquery-interval": 4000,					<br/>					"name": "Vlan2",					<br/>					"version": 3<br/>				}<br/>			}]<br/>		}<br/>	}<br/>} |



###### **Field Support:**    (RFC 8040)4.8.3. The "fields"Query Parameter

The"fields" query parameter is used to optionally identify data nodes within the target resource to be retrieved in a GET method. The client can use this parameter to retrieve a subset of all nodes in a resource.

| single  field                                                |
| ------------------------------------------------------------ |
| ***Request***     <br />curl -X GET "https://localhost/restconf/data/openconfignetwork-  instance:network-instances/network-instance=default/protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING/openconfig-network-instance-deviation:igmp-snooping/interfaces/interface=Vlan2**?fields=config/enabled**"  -H "accept: application/yang-data+json" -H "Content-Type:  application/yangdata+json"<br /> ***Response*:**  {<br />     "openconfig-network-instance- deviation:config": {<br />         "enabled": true<br />     }<br />  } |
| ***Request***   <br />curl -X GET "https://localhost/restconf/data/openconfig-networkinstance:  network-instances/network-instance=default/protocols  /protocol=IGMP_SNOOPING,IGMP-SNOOPING/openconfig-  network-instance-deviation:igmp-snooping**?content=all**"  -H "accept:application/yang-data+json" -H "Content-Type:  application/yangdata+json"<br /> ***Response*:**  {<br/>	"openconfig-network-instance-   deviation:igmpsnooping": {<br/>		"interfaces": {<br/>			"interface": [{<br/>				"config": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				},<br/>				"name": "Vlan1",<br/>				"state": {<br/>					"enabled": true,<br/>					"last-memberquery-interval": 2000,<br/>					"name": "Vlan1"<br/>				}<br/>			}, {<br/>				"config": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				},<br/>				"name": "Vlan2",<br/>				"state": {<br/>					"enabled": false,<br/>					"last-memberquery-interval": 4000,<br/>					"name": "Vlan2",<br/>					"version": 3<br/>				}<br/>			}]<br/>		}<br/>	}<br/>} |

| multiple leafs /leaflists                                    |
| ------------------------------------------------------------ |
| ***Request*** <br />curl -X GET "https://localhost/restconf/data/openconfignetwork-  instance:network-instances/network-instance=default  /protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING  /openconfig-network-instance-deviation:igmp-snooping  /interfaces/interface=Vlan2/state**?fields=enabled;  version**" -H "accept: application/yangdata+json" -H  "Content-Type: application/yang-data+json"<br /> ***Response*:**  {     <br />"openconfig-network-instance-deviation:state ": {<br />        "enabled": false,<br />         "version": 3<br />    }<br />  } |

| field expression ending  with container & without any intermediate list |
| ------------------------------------------------------------ |
| ***Request***<br />curl -X GET "https://localhost/restconf/data/openconfignetwork-  instance:network-instances/network-instance=default  /protocols/protocol=IGMP_SNOOPING,IGMP-SNOOPING  /openconfig-network-instance-deviation:igmp-snooping  /interfaces/interface=Vlan2"**?fields=state **"  -H "accept: application/yangdata+json" -H "Content-Type:  application/yang-data+json     <br />***Response*:**  {<br />     "openconfig-network-instance-deviation:"interface": [{<br />       "name":  "Vlan2",<br />        "state": {<br />          "enabled": false,<br />          "last-memberquery-interval":  4000,<br />          "name": "Vlan2",<br />          "version": 3<br />        }<br />    }]<br />  } |



# 3 Design

## 3.1 Overview
Sonic Management infra will be enhanced to support query parameters. Changes include

![qpFlowPic](C:\Users\marimuthu_sakthivel\Desktop\qpFlowPic.png)

***Rest server:***

​                 Rest server currently supports DEPTH based query parameter. This will be enhanced to handle CONTENT & FIELDS based query parameters, fill the QP info in the data-structure used by translib and will pass the same to translib.

***Translib:***

​                 Translib will pass the QP filled data-structure to the transformer-infra & apps.

***Transformer-infra:***

​                 Transformer infra will be enhanced to handle QP for GET request. Incoming QP (especially FIELDS option) will be validated first and processed appropriately per the QP. 

**DEPTH based QP:**

Infra will treat the incoming DEPTH QP as “current depth” level and will decrement it by 1 at every container & list level, while parsing Infra will fetch the data from the DB and fill the result-map, if the current depth is greater than 1. 

If a subtree is encountered while parsing, then the current depth will be passed to the subtree. The subtree will internally make use of current depth, process appropriately and fill the ygot accordingly. 

Infra will stop processing further when the current depth becomes0 and will return the response data back to the NBI. 

Refer below depth QP table, for each yang-component handled by the infra & subtree.

****

| **S.No.** | **Yang component** | **Current depth** | **Response  JSON**                     | **Comments**                             |
| --------- | ------------------ | ----------------- | -------------------------------------- | ---------------------------------------- |
| 1         | Leaf/leaflist      | 0                 | Data will  not be present              |                                          |
| 2         | Leaf/leaflist      | >0                | Data will  be present.                 |                                          |
| 3         | Container          | 1                 | Empty  container will not be  present. | This is a  deviation from RFC, due to restriction in  ygot. |
| 4         | Container          | >1                | Container  data will be  present.      |                                          |
| 5         | List               | 1                 | Empty  list will not be present.       | This is a  deviation from RFC, due to restriction in  ygot. |
| 6         | List               | >1                | List data will be present.             |                                          |

**CONTENT based QP:**

Infra will referthe yang node/component type in the yang-metadata and process accordingly.

In case of “config” CONTENT QP request, the infra investigates the yang-node-type of each container & list while parsing. If the type is RW, the list or container contents will be read from the DB and filled in result map. It will not process further if the container/list is of RO type. 

In case of“non-config” CONTENT QP request, infra reads the DB for RO type list &container yang-nodes and will fill the result-map with it. This case is special,i.e. a RO node can be present inside a RW node, in such a scenario, the infra will parse further into the RW node looking for RO nodes and process appropriately. 

If a subtree is encountered while parsing the GET request, it will be invoked,passing the CONTENT QP to it. The subtree will internally handle the request similar to the infra (as explained above) and will fill the ygot appropriately.

Refer below content QP table, for each yang-component handled by the infra & subtree.

| **Sr. No.** | **Yang Component**  | **Content type** | **Response JSON**                |
| ----------- | ------------------- | ---------------- | -------------------------------- |
| 1           | Leaf/leaflist (RO)  | config           | Data will not be  present.       |
| 2           | Leaf/leaflist (RW)  | config           | Data will be present.            |
| 3           | Leaf/leaflist (RO). | non-config       | Data will be present.            |
| 4           | Leaf/leaflist (RW)  | non-config       | Data will not be  present.       |
| 5           | Container (RO)      | config           | Data will not be  present.       |
| 6           | Container (RW)      | config           | Container data will be  present. |
| 7           | Container (RO)      | non-config       | Data will be present.            |
| 8           | Container (RW)      | non-config       | RO children will be  present.    |
| 9           | List (RO)           | config           | RO children will be  present.    |
| 10          | List (RW)           | config           | Data will be present.            |
| 11          | List (RO)           | non-config       | Data will be present.            |
| 12          | List (RW)           | non-config       | RO children will be  present.    |

**FIELDS based QP:**

Infra will be enhanced to support FIELDS QP. It will validate the fields given in the QP i.e. individual leaf/container or its relative path.

Infra looks at the FIELDS in QP and process them appropriately as given below.

·       type - single/multiple fields:

o  URI at container level: it reads table contents from the db for the incoming URI and returns the values for the requested field/fields.

o  URI at list level (without key): it reads table contents from the db for the incoming URI and returns the values in all the instances matching requested field/fields.

o  URI at list level (with key): it reads table contents from the db for the incoming URI list instance and returns the value matching requested field/fields.

·       type - child container fields path:

o  URI at container level and fields at child-container level (no intermediate list in container-path at fields): it reads table contents from the db for the incoming URI and returns all the leaves present in the requested container.

o  URI at list level (with key) and fields at child-container level(no intermediate list in container-path at fields):  it reads table contents from the db for the incoming URI list instance and returns all the contents of child-container at fields.

o  URI at list level (without key) and fields at child-container level (no intermediate list in container-path at fields):  it reads table contents from the db for the incoming URI list instance and returns all the contents of child-container at fields, for all the list instances..

If a subtree is encountered while parsing the GET request, it will be invoked, passing the FIELDS QP to it. The subtree will internally handle the request similar to the infra (as explained above) and will fill they got appropriately.

*Note:** FIELDS having list(with or without key) is not supported.*

****

| **Sr. No.** | **Yang Component**                       | **FIELDS type**                          | **Response JSON**                        |
| ----------- | ---------------------------------------- | ---------------------------------------- | ---------------------------------------- |
| 1           | Leaf/leaflist                            | single  leaf/leaflist                    | Only requested leaf/leaflist data will be present. |
| 2           | Leaf/leaflist                            | multiple  leaf/leaflist                  | All requested leaves/leaflist data will be present. |
| 3           | Complex node i.e. Container & leaf/leaflist | field-path ending with a leaf and sibling container &  without any intermediate list | All the contents inside the container  should be present. |

Support for multiple QPs in a single GET request URI.

| **QP  combination**                      | Supported |
| ---------------------------------------- | --------- |
| DEPTH  with CONTENT based QP             | Yes       |
| DEPTH  with FIELDS based QP              | No        |
| CONTENT(all)  with FIELDS based QP       | Yes       |
| CONTENT(config/non-config)  with FIELDS based QP | No        |
| DEPTH  with CONTENT & FIELDS             | No        |

**DEPTH with CONTENT based QP:**

​                 Infra will be enhanced to support DEPTH & CONTENT based QP combined in a single request URI. Please refer to the **DEPTH based QP** and **CONTENT based QP **sections, explained above for the behavior. DEPTH will be given high priority here.

Table: **Transformer function support for QP**

| **Transformer function** | **Needs enhancement to support QP** |
| ------------------------ | ----------------------------------- |
| Subtree  xfmr            | Yes                                 |
| Field  xfmr              | No                                  |
| Table  xfmr              | No                                  |
| Field name               | No                                  |
| Table  name              | No                                  |

Below are the new data structures added to support query parameters.

<u>In Translib:</u>

​	"QueryParameters" struct will be filled by the translib and passed to transformer-infra.

        type QueryParameters struct {
        	Depth   uint     // range 1 to 65535, default is <93>0<94> i.e. all
        	Content string   // all, config, nonconfig(REST)/state(GNMI), operational(GNMI only)
        	Fields  []string // list of fields from NBI
        }
        type GetRequest struct {
        	Path          string
        	FmtType       TranslibFmtType
        	User          UserRoles
        	AuthEnabled   bool
        	ClientVersion Version
        	QueryParams   QueryParameters
        }
<u>In Transformer:</u>

"QueryParams" struct will be used by the transformer infra and will be shared with the app subtree. This will part of "XfmrParams" struct.

    const (
    	...
    	QUERY_CONTENT_ALL         = 0
    	QUERY_CONTENT_CONFIG      = 1
    	QUERY_CONTENT_NONCONFIG   = 2
    	QUERY_CONTENT_OPERATIONAL = 3
    )
    type QueryParams struct {
        	depthEnabled      bool	//flag to indicate if "depth" is enabled
        	curDepth          uint	//current depth, will be decremented at each yang node level
        	content           uint8	//content type all/config/non-config/operational
        	fields            []string //list of fields(container, leaf/leaflist).List is not allowed.
        	//following attributes are for transformer infra use only
        	fieldsFillAll     bool	//flag to fill all fields in container/list
        	allowFieldsXpath  map[string]bool	//proceed further only if xpath is present in this set
        	tgtFieldsXpathMap map[string][]string	//process & fill data only if xpath is present in this map.
        }
        
        type XfmrParams struct {
        	....
        	queryParams    QueryParams
        }
## 3.2 DB Changes

N/A
### 3.2.1 CONFIG DB

N/A

### 3.2.2 APP DB

N/A

### 3.2.3 STATE DB

N/A

### 3.2.4 ASIC DB

N/A

### 3.2.5 COUNTER DB

N/A

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
N/A

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 Show Commands
#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
N/A

### 3.6.3 REST API Support

N/A

# 4 Flow Diagrams


# 5 Error Handling
Rest server will return error "400 Bad Request", if 

1.       DEPTH is out of range1-65535

2.       CONTENT is not one of"all", "config", "non-config" values.

3.       FIELDS type having list.

4.       If the"ietf-restconf-monitoring" module’s "restconf-state"container "capability" leaf-list has not included the DEPTH, CONTENT& FIELDS QP URIs. 

5.       DEPTH, CONTENT &FIELDS parameter is used for methods or resource types other  than for GET methods on API,  datastore, and data resources. if "fields" path is not valid xpath under the target GET request URI.

6.       Target URI points to a leaf/leaf-list and DEPTH is specified or CONTENT type doesn’t match the content type of the target leaf/leaf-list. 

7.       If more than one instance of a query parameter is present in a single request URI.

8.       Any QP other than DEPTH,CONTENT and FIELDS in request URI.

# 6 Serviceability and Debug
Appropriate QP support debug logs will be added in the rest, transformer-infra and subtree.

# 7 Warm Boot Support
N/A

# 8 Scalability
Describe key scaling factor and considerations.

# 9 Unit Test
·       Capability check.

·       DEPTH based QP test- cases:

Target URI at Module/Container/List, with depth N.

| **S.No.** | **Yang component** | **Response JSON**                        |
| --------- | ------------------ | ---------------------------------------- |
| 1         | Leaf/leaflist      | All  leaves/leaflist till N level should be present in response. |
| 2         | Container          | Contents  of the container till N-1 level should be present in response. |
| 3         | List               | Contents  of the list till N-1 level should be present in response. |

** **

·       CONTENTbased QP test- cases:

| **Sr No.** | **Yang Component**  | **Content type** | **Response JSON**                  |
| ---------- | ------------------- | ---------------- | ---------------------------------- |
| 1          | Leaf/leaflist (RO)  | config           | Data should not be  present.       |
| 2          | Leaf/leaflist (RW)  | config           | Data should be present.            |
| 3          | Leaf/leaflist (RO). | non-config       | Data should be present.            |
| 4          | Leaf/leaflist (RW)  | non-config       | Data should not be  present.       |
| 5          | Container (RO)      | config           | Data should not be  present.       |
| 6          | Container (RW)      | config           | Container data should  be present. |
| 7          | Container (RO)      | non-config       | Data should be present.            |
| 8          | Container (RW)      | non-config       | RO children should be present.     |
| 9          | List (RO)           | config           | RO children should be  present.    |
| 10         | List (RW)           | config           | Data should be present.            |
| 11         | List (RO)           | non-config       | Data should be present.            |
| 12         | List (RW)           | non-config       | RO children should be  present.    |

** **

** **

FIELDS based QP test- cases:****

| **FIELDS value**                         | **Description**                          |
| ---------------------------------------- | ---------------------------------------- |
| Singe  field                             | Return  only data node, matching the field. |
| Multiple  fields                         | Return  only data nodes, matching the fields |
| child  container fields path             | Return  all descendant data nodes, matching the fields inside child container path. |
| fields at  current level & child container fields path | Return  data nodes matching the fields at current level and all descendant data  nodes, matching the fields inside child container path. |

Sample FIELDS queries:

·       /restconf/data/openconfig-interfaces:interfaces/interface?fields=state(name;oper-status;counters) 

·       /restconf/data/openconfig-interfaces:interfaces/interface[name=Ethernet0] ?fields=container (name;admin-status) 

·       /restconf/data/openconfig-interfaces:interfaces/interface[name=Ethernet0]/state?fields=counter(in-pkts) 

# 10 Internal Design Information
