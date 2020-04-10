# Static IP route Configuration

Implement Static IP route Configuration via  CLI/REST/gNMI  in SONiC management framework for non-management routes.

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
| Rev |     Date    |       Author                | Change Description                |
|:---:|:-----------:|:---------------------------:|-----------------------------------|
| 0.1 | 03/18/2020  |  Sucheta Mahara             | initial draft                     |
|  0.2| 03/20/20202 |  Venkatesan Mahalinga       | draft                             |
| 0.2 | 03/23/2020  |  Zhenhong Zhao              | FRR Config Support             |

# About this Manual
This document provides general information about configuring static routes via Management CLI/REST/gNMI in Sonic.
# Scope
Covers general design for supporting static routes in SONiC Management framework.

# Definition/Abbreviation

### Table 1: Abbreviations
| **Term**                 | **Meaning**                         |
|--------------------------|-------------------------------------|
| IP                     |  Internet Protocol       |
| VRF                     | Virtual routing and forwarding


# 1 Feature Overview

The documents covers the various interfaces for configuring static routes using SONiC management framework.

## 1.1 Requirements

### 1.1.1 Functional Requirements

Provide ability to configure IPv4 and IPv6 static routes using SONiC management framework.

### 1.1.2 Configuration and Management Requirements
 - Implement Static ip route CLI Commands.
 - REST set/get support for Static IPv4 and IPv6 routes.
 - gNMI set/get support for Static IPv4 and IPv6 routes.

### 1.1.3 Scalability Requirements
### 1.1.4 Warm Boot Requirements

## 1.2 Design Overview
### 1.2.1 Basic Approach
### 1.2.2 Container
### 1.2.3 SAI Overview
# 2 Functionality
## 2.1 Target Deployment Use Cases
## 2.2 Functional Description
# 3 Design
## 3.1 Overview
An existing table STATIC_ROUTE (which is not used currently) will be used to write static route from the transformer for any CLI, rest or gNMI request. This table will be monitored by bgpcfgd daemon and the config will be sent to vtysh shell for configuring in FRR.
## 3.2 DB Changes
### 3.2.1 CONFIG DB
STATIC_ROUTE table in config DB will be used to  support this feature.

#### 3.2.1.1 STATIC_ROUTE
```JSON
;Defines IP static route  table
;
;Status: stable

key                 = STATIC_ROUTE|vrf-name|prefix ;
vrf-name            = 1\*15VCHAR ; VRF name
prefix              = IPv4Prefix / IPv6prefix
nexthop             = IPv4Address / IPv6Address; List of gateway addresses;
ifname              = List of interfaces
distance            = {0..255};List of distances.
                      Its a Metric used to specify preference of next-hop
                      if this distance is not set, 0 will be set to maintain the set;
nexthop-vrf         =  1\*15VCHAR ; list of next-hop VRFs. It should be set only if ifname or nexthop IP  is not
                       in the current VRF . The value is set to VRF name
                       to which the interface or nexthop IP  belongs for route leaks.
blackhole           =  List of boolean; true if the next-hop route is blackholed.                     
```
The nexthop-vrf if set, will allow to create a leaked route in the current VRF(vrf-name). The vrf-name, nexthop-vrf, prefix, ifname, distance and blackhole are all parameters required to configure static routes and route leaks in vtysh.
If an interface is moved from one VRF to another and it exist in the STATIC_ROUTE table, error will be returned by the backend. User is expected to remove all static routes pertaining to the interface before binding the interface to a different VRF.
If prefix is IPv4Prefix nexthop will have  IPv4Address and if  prefix is IPv6Prefix nexthop will have  IPv6Address.
In this table each entry based on the index in the lists of  nexthop, ifname, distance, nexthop-vrf and blackhole  is a set. Together based on the index they specify one next-hop entry as there can be multiple next-hops for a prefix. Empty string will be used to complete the set if required.

In the example -1 table below (0.0.0.0, Ethernet0, 10, default, false) , (2.2.2.2, "", 0,"", false), (0.0.0.0, Ethernet12, 30, Vrf-GREEN, false) are the 3 sets defined for 3 configured next-hops for prefix 10.11.1.0/24 in Vrf-RED. 
In example -2  the blackhole is true for second index and  only distance is relevant in blackholed route. Due to blackhole entry (with metric 40) all packets matching 10.12.11.0/24 will be discarded if other specified  nexthop is inactive.

```JSON
Example -1 :--

key                 = STATIC_ROUTE|Vrf-RED|10.11.1.0/24;
vrf-name            = Vrf-RED
prefix              = 10.11.1.0/24
nexthop             = 0.0.0.0, 2.2.2.1, 0.0.0.0
ifname              = "Ethernet0", "", "Ethernet12" 
distance            = 10,0,30
nexthop-vrf         = "default", "" , "Vrf-GREEN"
blackhole           = false, false, false

EXAMPLE 2:-
key                 = STATIC_ROUTE|default|10.12.11.0/24;
vrf-name            = default
prefix              = 10.12.11.0/24
nexthop             = 2.2.2.3, ""
ifname              = "", ""
distance            = 10,40
nexthop-vrf         = "",""
blackhole           = false, true


```


Note: This model is proposed in line with ROUTE_TABLE model in application DB used for route updates and "vrf hld" description of STATIC_ROUTE table (which is currently not in use). Some default values like 0.0.0.0 and empty strings are used to complete a set. See the CLI example later to see how the table is filled up step-by-step.


### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 Switch State Service Design
### 3.3.1 Orchestration Agent
### 3.3.2 Other Process
## 3.4 SyncD
## 3.5 SAI
## 3.6 User Interface
### 3.6.1 Data Models

The following open config YANG model will be used to implement this feature.

    1) openconfig-network-instance.yang
    2) openconfig-local-routing.yang
openconfig-local-routing-ext.yang will be used to specify unsupported fields and extensions.

Supported YANG containers:-
```diff
module: openconfig-network-instance
    +--rw network-instances
       +--rw network-instance* [name]
          +--rw protocols
             +--rw protocol* [identifier name]
                +--rw identifier    -> ../config/identifier
                +--rw name          -> ../config/name
                +--rw static-routes
                +--rw static* [prefix]
                    +--rw prefix       -> ../config/prefix
                    +--rw config
                    |    +--rw prefix?  inet:ip-prefix
                    +--ro state
                    |  +--ro prefix?   inet:ip-prefix
                    +--rw next-hops
                      +--rw next-hop* [index]
                         +--rw index                -> ../config/index ----(Read note below)
                         +--rw config
                         |  +--rw index?      string
                         |  +--rw next-hop?   union
                         |  +--rw metric?     uint32
                         |  +--rw oc-local-routing-ext:nexthop-vrf-name?   string
                         |  +--rw oc-local-routing-ext:blackhole?          boolean
                         +--ro state
                         |  +--ro index?      string
                         |  +--ro next-hop?   union
                         |  +--ro metric?     uint32
                         |  +--rw oc-local-routing-ext:nexthop-vrf-name?   string
                         |  +--rw oc-local-routing-ext:blackhole?          boolean
                         +--rw interface-ref
                         |  +--rw config
                         |  |   +--rw interface?   -> /oc-if:interfaces/interface/name
                         |  +--ro state
                         |      +--ro interface?   -> /oc-if:interfaces/interface/name



```
New Parameters

|    Keyword    | Description |
|:-----------------:|:-----------:|
oc-local-routing-ext:nexthop-vrf-name|Specify the nexthop-vrf incase interface or next-hop is not in current instance(i.e VRF). This parameter is explicitly required  by vtysh to correctly install route leaks.
oc-local-routing-ext:blackhole | If set to true the nexhop is a blackholed route. Only metric is relevant when configuring blackhole next-hop for a prefix.

Note: Each next-hop entry has a key called "index" in openconfig yang as shown above. This key is used to uniquely identify a entry in the list of next-hops. This key will be formed based on "interface (interface name if present) + next-hop (next-hop-ip if present) + vrf-name" and is expected to be provided correctly  by the user for non-blackhole routes. For blackhole route DROP + vrf-name will be used as key. Either interface name  or next-hop-ip or both or blackhole  should be present for any route to be accessed. i.e Ethernet0_2.2.2.2_default, 3.3.3.3_Vrf-RED, DROP_Vrf-GREEN. This key will not be stored in config DB. For default instance vrf-name in the key is optional.


A new sonic-static-route.yang is defined to store entries in STATIC_ROUTE table in configDB.

```diff

module: sonic-static-route
  +--rw sonic-static-route
     +--rw STATIC_ROUTE
        +--rw STATIC_ROUTE_LIST* [vrf-name prefix]
           +--rw vrf-name   union
           +--rw prefix     inet:ip-prefix
           +--rw nexthop*   inet:ip-address
           +--rw ifname*    union
           +--rw distance*  uint32
           +--rw nexthop-vrf* string
           +--rw blackhole*   boolean


```

### 3.6.2 CLI
#### 3.6.2.1 Configuration Commands
#### 3.6.2.2 ip/ipv6 route config command
ip route command is used to configure IPv4  static routes in SONiC.
ipv6 route command is used to configure IPv6 static routes in SONiC.
##### 3.6.2.2.1
Syntax

Vrf (for default instance) and distance metric are optional in the CLI.

```
ip route [vrf <vrf-name>] <prefix: A.B.C.D/mask> {[interface <interface-name>] | [<next-hop-ip>] | [<next-hop-ip> interface <interface-name>]| [blackhole]} [nexthop-vrf <vrf-name>] <distance Metric>
```

```
ipv6 route [vrf <vrf-name>] <prefix: A.B.C.D/mask> {[interface <interface-name>] | [<next-hop-ip>] | [<next-hop-ip> interface <interface-name>]|[blackhole]} [nexthop-vrf <vrf-name>] <distance Metric>

```


Syntax Description:

|    Keyword    | Description |
|:-----------------:|:-----------:|
| vrf | The static routes will be configured in the specified VRF. If not specified, default VRF will be used.
| prefix | This is the destination prefix for IPv4 or IPv6 routes.
| interface | Specifies the interface to be used for this route. Specify nexthop-vrf correctly if interface is in another VRF.
| next-hop-ip | This provides the gateway IP for the prefix. Specify nexthop-vrf correctly if this IP is in another VRF.
| distance Metric| Specifies distance value for this route. Value from 1 to 255.
|nexthop-vrf| Specifies nexthop-vrf if interface or next-hop-ip is in another VRF.
|blackhole| Specifies if this nexthop is to be blackholed. Only distance metric is relevant for blackhole.


Example:

#### IPv4 examples
````
sonic(config)# ip route 10.1.1.1/24 10.1.1.3

In configDB new STATIC_ROUTE table will be filled with following entries for default VRF and prefix:-
key                 = STATIC_ROUTE|default|10.1.1.1/24;
vrf-name            = default
prefix              = 10.1.1.1/24
nexthop             = 10.1.1.3
ifname              = ""
distance            = 0
nexthop-vrf         = ""
blackhole           = false


sonic(config)# ip route 10.1.1.1/24 Ethernet12 nexthop-vrf Vrf-RED  20
Assumption is Ethernet12 is bound to Vrf-RED.
STATIC_ROUTE table entries are updated for newly added route:-
key                 = STATIC_ROUTE|default|10.1.1.1/24;
vrf-name            = default
prefix              = 10.1.1.1/24
nexthop             = 10.1.1.3, 0.0.0.0
ifname              = "", Ethernet12
distance            = 0, 20
nexthop-vrf         = "", Vrf-RED
blackhole           = false, false

Note: "show ip route" will also show installed static routes along with other routes.

sonic(config)# do show ip route vrf <vrf-name>
````

````

sonic(config)# ip route vrf Vrf-RED 10.5.6.6/24 10.5.6.1 nexthop-vrf default 10

Assumption is 10.5.6.1 is in default VRF.
A new STATIC_ROUTE table will be filled with following entries for Vrf-RED and prefix:-
key                 = STATIC_ROUTE|Vrf-RED|10.5.6.6/24;
vrf-name            = Vrf-RED
prefix              = 10.5.6.6/24
nexthop             = 10.5.6.1
ifname              = ""
distance            = 10
nexthop-vrf         = default
blackhole           = false




````
#### IPv6 examples
````
sonic(config)# ipv6 route 2::/64 Ethernet16

sonic(config)# ipv6 route 2001:FF21:1:1::/64 18:2:1::1 100

sonic(config)# ipv6 route 2111:dddd:0eee::22/128 blackhole 200

Note: "show ipv6 route"  will show static routes along with other routes.

sonic(config)# do show ipv6 route vrf <vrf-name>

````
##### 3.6.2.2.2 ipv4 /ipv6 Command to delete a next-hop.

The vrf is an optional parameter for default instance.

```
no ip route vrf <vrf-name> <prefix: A.B.C.D/mask> {[interface <interface-name>] | [<next-hop-ip>] | [<next-hop-ip> interface <interface-name>]|[blackhole]}

```

```
no ipv6 route vrf <vrf-name> <prefix: A.B.C.D/mask> {[interface <interface-name>] | [<next-hop-ip>] | [<next-hop-ip> interface <interface-name>][blackhole]}
```
#### 3.6.2.3 Debug Commands
#### 3.6.2.4 IS-CLI Compliance
The following table maps SONiC CLI commands to corresponding IS-CLI commands. The compliance column identifies how the command comply to the IS-CLI syntax:

- **IS-CLI drop-in replace**  \u2013 meaning that it follows exactly the format of a pre-existing IS-CLI command.
- **IS-CLI-like**  \u2013 meaning that the exact format of the IS-CLI command could not be followed, but the command is similar to other commands for IS-CLI (e.g. IS-CLI may not offer the exact option, but the command can be positioned is a similar manner as others for the related feature).
- **SONiC** - meaning that no IS-CLI-like command could be found, so the command is derived specifically for SONiC.

|CLI Command|Compliance|IS-CLI Command (if applicable)| Link to the web site identifying the IS-CLI command (if applicable)|
|:---:|:-----------:|:------------------:|-----------------------------------|
|ip route |IS-CLI-like || |
|ipv6 route| IS-CLI-like| | |
|no ip route |IS-CLI-like || |
|no ipv6 route |IS-CLI-like| | |


### 3.6.3 REST API Support
#### 3.6.3.1
##### Following REST operations will be supported

1. GET ,POST, PATCH and DELETE supported at /restconf/data/openconfig-network-instance:network-instances/network-instance={name}/protocols/protocol={identifier},{name1}/static-routes
2. GET , POST, PATCH and DELETE supported at /restconf/data/openconfig-network-instance:network-instances/network-instance={name}/protocols/protocol={identifier},{name1}/static-routes/static={prefix}
3. GET, POST and DELETE supported at /restconf/data/openconfig-network-instance:network-instances/network-instance={name}/protocols/protocol={identifier},{name1}/static-routes/static={prefix}/next-hops/next-hop={index}

## 3.7 FRR Configuration Support
### 3.7.1 Configuration Mapping to FRR
Bgpcfgd daemon will be used to forward configurations stored in STATIC_ROUTE table to FRR staticd daemon. It will subscribe to listen to STATIC_ROUTE table and if there is data update, it will convert associated data to FRR vtysh command request and send to FRR daemon to configure static route on Linux kernel.
#### 3.7.1.1 Table entry to command mapping
FRR vtysh command is composed with VRF/IP_prefix and nexthop data fields in STATIC_ROUTE table entry
#### FRR command syntax
```
configure terminal
vrf <src_vrf>
[no ]ip route <ip_prefix> [<nexthop_ip>] [<interface>] [<distance>] [nexthop-vrf <nh_vrf>]
```
#### Mapping from table entry to FRR command arguments
|Parameter Name|Table Entry Key or Field|Type|Default or Null Value|
|:---:|:-----------:|:------------------:|-----------------------------------|
|src_vrf|first entry key*|optional for default VRF|"default"|
|ip_prefix|second entry key*|mandatory|-|
|nexthop_ip|entry field **nexthop****|optional if ifname is set or blackhole is true |"0.0.0.0" or "::"***|
|interface|entry field **ifname****|optional if nexthop_ip is set or blackhole is true |""|
|distance|entry field **distance****|optional|"0"|
|nexthop_vrf|entry field **nexthop-vrf****|required for route-leak case else optional |""|
|blackhole|entry field **blackhole***|required for blackhole next-hop else optional | false|

Note:
- *If table entry key contains only one item, it should be prefix_ip and src_vrf will be used with default value "default".
- **Each argument uses one item of corresponding list in table entry. If the item in list is "Null" value, this optional argument will not be added to mapped FRR commnand.
- ***The "Null" value of nexthop_ip should be chosen based on the address family of ip_prefix

#### Example of table entry and correspoinding FRR runnning config
Data in STATIC_ROUTE table:
```
127.0.0.1:6379[4]> hgetall STATIC_ROUTE|Vrf-test|1.1.1.0/16
1) "nexthop@"
2) "2.2.2.2,0.0.0.0"
3) "distance@"
4) "10,20"
5) "ifname@"
6) "Ethernet0,Ethernet4"
7) "nexthop-vrf@"
8) "Vrf-BLUE,Vrf-RED"
9) "blackhole@"
10) "false,false"
```
FRR running config:
```
!
vrf Vrf-test
 ip route 1.1.0.0/16 2.2.2.2 Ethernet0 10 nexthop-vrf Vrf-BLUE
 ip route 1.1.0.0/16 Ethernet4 20 nexthop-vrf Vrf-RED
 exit-vrf
!
```
### 3.7.2 Configuration Reload
All static route configurations were persistently stored in config DB STATIC_ROUTE table. After BGP container restarts, the configuration in DB needs to be re-applied. This configuration reload is done by generating staticd.conf file before FRR staticd daemon starts. A jinja template file will be used to map table entries to fill in staticd.conf file. The generated conf file is loaded by FRR daemon to configure static routes to system.

# 4 Flow Diagrams

# 5 Error Handling

# 6 Serviceability and Debug
# 7 Warm Boot Support

# 8 Scalability

# 9 Unit Test and automation
The following test cases will be tested using CLI/REST/gNMI management interfaces.
#### Static route Unit test cases:

1) Verify creation deletion of multiple next-hops for a prefix list in default vrf.
2) Verify creation deletion of multiple next-hops for a prefix list in not-default vrf.
3) Verify creation deletion of multiple next-hops for a prefix list for route leak case where the specified interface belongs to a different VRF.
4) Verify the get/set operation passes for a particular next-hop when supplying the correct index as key.
#### Automation
Spytest cases will be incremented for new CLI and APIs.
