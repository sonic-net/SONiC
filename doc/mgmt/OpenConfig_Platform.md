# OpenConfig support for Platform Transceiver.

# High Level Design Document
#### Rev 0.2

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Scope](#scope)
  * [Definition/Abbreviation](#definitionabbreviation)
  * [1 Feature Overview](#1-feature-overview)
	* [1.1 Requirements](#11-requirements)
	  * [1.1.1 Functional Requirements](#111-functional-requirements)
	* [1.2 Design Overview](#12-design-overview)
	  * [1.2.1 Basic Approach](#121-basic-approach)
	  * [1.2.2 Container](#122-container)
	  * [1.2.3 The name of components](#123-the-name-of-components)
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
	  * [3.3.3 gNMI Support](#333-gnmi-support)
	* [3.4 Behavior for breakout ports.](#34-behavior-for-breakout-ports)
  * [4 Mapping between Openconfig YANG and Redis DB](#4-mapping-between-openconfig-yang-and-redis-db)
  * [5 Error Handling](#5-error-handling)
  * [6 Unit Test Cases](#6-unit-test-cases)
	* [6.1 Functional Test Cases](#61-functional-test-cases)
	* [6.2 Negative Test Cases](#62-negative-test-cases)
  
# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

[Table 2: Mapping attributes between OpenConfig YANG and RedisDB](#table-2-mapping-attributes-between-openconfig-yang-and-redisdb)

# Revision
| Rev |     Date    |       Author          | Change Description                |
|:---:|:-----------:|:---------------------:|-----------------------------------|
| 0.1 | 11/22/2024  | Kanji Nakano / Koji Sugisono | Initial version                   |
| 0.2 | 1/28/2025  | Kanji Nakano / Koji Sugisono | Adding a support for CRITICAL/WARNING threshold parameters         |

# About this Manual
This document provides general information about the OpenConfig telemetry for state information corresponding to openconfig-platform-transceiver.yang and its sub-modules for transceiver components.


# Scope
- This document describes the high level design of OpenConfig telemetry for states of transceiver components via gNMI in SONiC.
- This does not cover the SONiC KLISH CLI.
- This covers openconfig-platform-transceiver.yang and its sub-modules.
- This does not cover gNMI SUBSCIRBE STREAM ON_CHANGE and TARGET_DEFINED.
- This does not ensure to show the information on breakout ports and physical channels mapped to each port(e.g.,100G -> 25x4G 4 ports). 
- Supported attributes in OpenConfig YANG tree:

```  
module: openconfig-platform
  +--rw components
	 +--rw component* [name]
		+--ro state
		|  +--ro serial-no?                             string
		+--rw oc-transceiver:transceiver
		   +--ro oc-transceiver:state
		   |  +--ro oc-transceiver:connector-type?      identityref
		   |  +--ro oc-transceiver:vendor?              string
		   |  +--ro oc-transceiver:vendor-part?         string
		   |  +--ro oc-transceiver:serial-no?           string
		   |  +--ro oc-transceiver:date-code?           oc-yang:date-and-time
		   |  +--ro oc-transceiver:supply-voltage
		   |  |  +--ro oc-transceiver:instant?          decimal64
		   |  +--ro oc-transceiver:laser-bias-current
		   |     +--ro oc-transceiver:instant?          decimal64
		   +--rw oc-transceiver:physical-channels
		   |  +--rw oc-transceiver:channel* [index]
		   |     +--ro oc-transceiver:state
		   |        +--ro oc-transceiver:laser-temperature
		   |        |  +--ro oc-transceiver:instant?    decimal64
		   |        +--ro oc-transceiver:output-power
		   |        |  +--ro oc-transceiver:avg?        decimal64
		   |        +--ro oc-transceiver:input-power
		   |       |  +--ro oc-transceiver:instant?    decimal64
		   |        +--ro oc-transceiver:laser-bias-current
		   |           +--ro oc-transceiver:instant?    decimal64
		   +--rw oc-transceiver:thresholds
		   |  +--rw oc-transceiver:threshold [severity *1]
		   |     +--ro oc-transceiver:state
		   |        +--ro oc-transceiver:severity		identityref
		   |        +--ro oc-transceiver:output-power-upper decimal64
		   |        +--ro oc-transceiver:output-power-lower decimal64
		   |        +--ro oc-transceiver:input-power-upper decimal64
		   |        +--ro oc-transceiver:input-power-lower decimal64
		   |        +--ro oc-transceiver:laser-bias-current-uppwer decimal64
		   |        +--ro oc-transceiver:laser-bias-current-lower decimal64
```  

*1: The latest version supports CRITICAL and WARNING as the severity level.

# Definition/Abbreviation
### Table 1: Abbreviations
| **Term**                 | **Definition**                         |
|--------------------------|-------------------------------------|
| YANG                     | Yet Another Next Generation: modular language representing data structures in an XML tree format        |
| gNMI                     | gRPC Network Management Interface: used to retrieve or manipulate the state of a device via telemetry or configuration data         |
| XML                     | eXtensible Markup Language   |

# 1 Feature Overview
## 1.1 Requirements
### 1.1.1 Functional Requirements
1. Provide support for OpenConfig YANG models.
2. Support telemetry for following read only parameters on transceiver components via REST and gNMI.
3. Add support for following features:
- serial-no
- connector-type
- vendor
- vendor-part
- date-code
- supply-voltage
- laser-temperature
- output-power
- input-power
- laser-bias-current 
- thresholds
  - output-power-upper/lower
  - input-power-upper/lower
  - laser-bias-current-upper/lower

## 1.2 Design Overview
### 1.2.1 Basic Approach
SONiC already supports telemetry for parameters like packet counters with methods such as Get via REST and gNMI. This feature adds support for telemetry for states of transceiver components with gNMI and YANG models of openconfig-transceiver.yang and with REST based on translib infra.

### 1.2.2 Container
The code changes for this feature are part of *Management Framework* container which includes the REST server and *gnmi* container for gNMI support in *sonic-mgmt-common* repository.

### 1.2.3 The name of components
openconfig-platform.yang does not hierarchically define their components.
This design uses the name comprised of a prefix of " transceiver_" and the interface name managed by SONiC to specify the path of the target transceiver components for REST/gNMI without the the name conflicts(e.g., “transceiver_Ethernet0”).

# 2 Functionality
## 2.1 Target Deployment Use Cases
1. REST client through which the user can GET operations on the supported YANG paths.
2. gNMI client with support for capabilities of GET / SUBSCRIBE ONCE, POLL, STREAM SAMPLE based on the supported YANG models.

# 3 Design
## 3.1 Overview
This HLD design is in line with the [Management Framework HLD](https://github.com/project-arlo/SONiC/blob/354e75b44d4a37b37973a3a36b6f55141b4b9fdf/doc/mgmt/Management%20Framework.md)

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
Data models for this feature are based on Openconfig-platform.yang(ver 0.27.0) and openconfig-platform-transceiver.yang(ver 0.14.0).

### 3.3.2 REST API Support

#### 3.3.2.1 GET
Supported 

Sample GET output for platform/components/component/transceiver/state/supply-voltage/instant node:

```
curl -ksX GET "https://<ip:port>/restconf/data/openconfig-platform:components/component=transceiver_Ethernet0/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant" | jq
{
  "openconfig-platform-transceiver:instant": "3.29"
}
```

### 3.3.3 gNMI Support

#### 3.3.3.1 GET
Supported.

Sample GET output for platform/components/component/transceiver/state/supply-voltage/instant node:
```
$ gnmic get -a <ip:port> --skip-verify --path "/openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant" --target OC-YANG
[
  {
	"source": " <ip:port>",
	"timestamp": 1732080919120211411,
	"time": "2024-11-20T14:35:19.120211411+09:00",
	"target": "OC-YANG",
	"updates": [
	  {
		"Path": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant",
		"values": {
		  "openconfig-platform:components/component/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant": {
			"openconfig-platform-transceiver:instant": "3.29"
		  }
		}
	  }
	]
  }
]
```

#### 3.3.3.2 SUBSCRIBE
Sample telemetry logs with once mode on platform/components/component/transceiver/state/supply-voltage/instant node
```
gnmic sub -a <ip:port> --skip-verify --path "/openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant" --target OC-YANG --mode "once"
{
  "source": " <ip:port>",
  "subscription-name": "default-1732080713",
  "timestamp": 1732080919361911393,
  "time": "2024-11-20T14:35:19.361911393+09:00",
  "prefix": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage",
  "target": "OC-YANG",
  "updates": [
	{
	  "Path": "instant",
	  "values": {
		"instant": 3.29
	  }
	}
  ]
}
```

Sample telemetry logs with poll mode on platform/components/component/transceiver/state/supply-voltage/instant node
```
gnmic sub -a <ip:port> --skip-verify --path "/openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant" --target OC-YANG --mode "poll"
{
  "timestamp": 1732085028739414967,
  "time": "2024-11-20T15:43:48.739414967+09:00",
  "prefix": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage",
  "target": "OC-YANG",
  "updates": [
	{
	  "Path": "instant",
	  "values": {
		"instant": 3.3
	  }
	}
  ]
}
{
  "sync-response": true
}
received sync response 'true' from '<ip:port>'
{
  "timestamp": 1732085031421688045,
  "time": "2024-11-20T15:43:51.421688045+09:00",
  "prefix": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage",
  "target": "OC-YANG",
  "updates": [
	{
	  "Path": "instant",
	  "values": {
		"instant": 3.3
	  }
	}
  ]
}
```

Sample telemetry logs with stream sample mode on platform/components/component/transceiver/state/supply-voltage/instant node

```
gnmic sub -a <ip:port> --skip-verify --path "/openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage/instant" --target OC-YANG --mode "stream" --stream-mode "sample"
{
  "sync-response": true
}
{
  "source": " <ip:port>",
  "subscription-name": "default-1732072116",
  "timestamp": 1732072322342759015,
  "time": "2024-11-20T12:12:02.342759015+09:00",
  "prefix": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage",
  "target": "OC-YANG",
  "updates": [
	{
	  "Path": "instant",
	  "values": {
		"instant": 3.3
	  }
	}
  ]
}
{
  "source": " <ip:port>",
  "subscription-name": "default-1732072116",
  "timestamp": 1732072342354565575,
  "time": "2024-11-20T12:12:22.354565575+09:00",
  "prefix": "openconfig-platform:components/component[name=transceiver_Ethernet0]/openconfig-platform-transceiver:transceiver/state/supply-voltage",
  "target": "OC-YANG",
  "updates": [
	{
	  "Path": "instant",
	  "values": {
		"instant": 3.3
	  }
	}
  ]
}
```

## 3.4 The behavior for breakout ports.
As of the timing this HLD is published, this code returns some information on specified breaktout port. However, the information does not include the physical channel the breakout port uses. As of the moment this HLD is published, SONiC does not have the function to show the mapping between a breakout port and the used physical channel. Then, the information on a breakout port this code provides relates to a physical channel and there is no method which physical channel the breakout port uses.

# 4 Mapping between Openconfig YANG and Redis DB
### Table 2: Mapping attributes between OpenConfig YANG and RedisDB:

<table rules="all">
	<tr style="background-color:turquoise">
		<th>Openconfig Yang</th>
		<th colspan=3> Redis DB</th>
	</tr>
	<tr style="background-color:paleturquoise">
		<th>Node</th>
		<th align="center">DB Name</th>
		<th align="center">Table Name</th>
		<th align="center">Object</th>
	</tr>
	<tr>
		<th align="left">openconfig-platform.yang</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 1em;">components</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 2em;">component</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 3em;">state</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 4em;">serial-no</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>serial</td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 3em;">transceiver</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 4em;">state</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">connector-type</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>connector</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">vendor</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>manufacturer</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">vendor-part</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>vendor_oui</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">serial-no</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>serial</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">date-code</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_INFO</td>
		<td>vendor_date</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:5em;">supply-voltage/instant</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_SENSOR</td>
		<td>voltage</td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 4em;">physical-channels</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 5em;">channel</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 6em;">state</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-temperature/instant</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_SENSOR</td>
		<td>temperature</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">output-power/instant</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_SENSOR</td>
		<td>tx1power, tx2power, tx3power, tx4power</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">input-power/instant</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_SENSOR</td>
		<td>rx1power, rx2power, rx3power, rx4power</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-bias-current/instant</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_SENSOR</td>
		<td>tx1bias, tx2bias, tx3bias, tx4bias</td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 4em;">thresholds</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 5em;">threshold[WARNING]</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 6em;">state</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">output-power-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txpowerhighwarning</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">output-power-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txpowerlowwarming</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">input-power-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>rxpowerhighwarning</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">input-power-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>rxpowerlowwarning</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-bias-current-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txbiashighwarning</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-bias-current-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txbiaslowwarning</td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 5em;">threshold[CRITICAL]</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left: 6em;">state</th>
		<td></td>
		<td></td>
		<td></td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">output-power-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txpowerhighalarm</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">output-power-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txpowerlowalarm</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">input-power-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>rxpowerhighalarm</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">input-power-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>rxpowerlowalarm</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-bias-current-upper</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txbiashighalarm</td>
	</tr>
	<tr>
		<th align="left" style="padding-left:7em;">laser-bias-current-lower</th>
		<td>State_DB</td>
		<td>TRANSCEIVER_DOM_THRESHOLD</td>
		<td>txbiaslowalarm</td>
	</tr>
</table>

# 5 Error Handling
Invalid operations will report an error.
# 6 Unit Test cases
## 6.1 Functional Test Cases
Operations: 
gNMI- Get / Subscribe
REST - GET

1.	Verify that operations supported for gNMI/REST works fine for serial-no of transceiver.
2.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:connector-type.
3.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:vendor.
4.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:vendor-part.
5.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:serial-no.
6.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:date-code.
7.	Verify that operations supported for gNMI/REST works fine for supply-voltage of transceiver.
8.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:laser-temperature.
9.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:output-power.
10.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:input-power.
11.	Verify that operations supported for gNMI/REST works fine for oc-transceiver:laser-bias-current.


## 6.2 Negative Test Cases
1. Verify that any operation on unsupported paths give a proper error.
2. Verify that GET on components with non-existing component name give a proper error.
3. Verify that GET on physical-channels with non-existing physical-channel index give a proper error.