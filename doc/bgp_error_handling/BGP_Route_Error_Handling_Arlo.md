


  
# BGP Route Install Error Handling
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
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 05/07/2019  |   Sudhanshu Kumar  | Initial version                   |

# About this Manual
This document provides information about how to handle the "route add failure in hardware" related errors in BGP in SONIC.
# Scope
This document describes the high level design of BGP route install error handling feature. Implementation for warm reboot and GR for BGP is out of scope for this feature. When route installation fails in hardware due to table full, BGP may retry again when some routes get deleted. This Retry mechanism in BGP for failed routes will not be implemented in this release.

# Definition/Abbreviation
### Table 1: Abbreviations

| **Term**          | ***Meaning***           |
|-------------------|-------------------------|
| BGP               | Border Gateway Protocol |
| GR                | Graceful Restart        |
| SONIC             | Software for Open Networking in the Cloud                        |
| FRR    	        |  FRRouting                       |
| FPM               |  Forwarding Plane Manager        |
| SwSS              |  SONiC Switch State Service      |
# 1 Requirement Overview
 When BGP learns a prefix, it sends it to route table manager(Zebra). The routes are installed in kernel and sent to APP_DB via fpmsyncd. 
The Orchagent reads the route from APP_DB, creates new resources like nexthop or nexthop group Id and installs the route in ASIC_DB. The syncd triggers the appropriate SAI API and route is installed in hardware. The CRM manages the count of critical resources allocated by orchagent through SAI API.
Due to resource allocations failures in hardware, SAI API calls can fail and these failures should be notified to Zebra and BGP.
On learning the prefix, BGP can immediately advertise the prefix to its neighbors. However, if the error-handling feature is enabled, BGP waits for success notification from hardware before advertising the same to its peers. If the hardware returns error, the routes are not advertised to the peers. 

## 1.1 Functional Requirements

 

 1. BGP should not advertise the routes which have failed to be installed in hardware.
 1. BGP should mark the routes which are not installed in hardware as  "FIB-install pending" routes in its RIB-IN table.
 1. Zebra should mark the routes which are not successfully installed in hardware as failed routes.

## 1.2 Configuration and Management Requirements
## 1.3 Scalability Requirements
## 1.4 Warm Boot Requirements
   There is no change needed in BGP warm reboot for supporting this feature.
# 2 Functionality
Refer to section 1

## 2.1 Target Deployment Use Cases

## 2.2 Functional Description
Refer to section 1.1

# 3 Design
## 3.1 Overview
On enabling the error-handling feature, fpmsyncd subscribes to the changes in the ERROR_ROUTE_TABLE entries. Whenever the error status in ERROR_ROUTE_TABLE is updated, fpmsyncd is notified. It then sends a message to Zebra's routing table to take appropriate action.
Zebra should lookup the route and mark it as not installed in hardware. It should create a route-netlink message to withdraw this state in kernel. Also, it sends message to the source protocol for the route (BGP). 
BGP marks the route as not installed in hardware and does not advertise the route to its peers. It should mark the route in RIB-IN as not installed in hardware and remove it from RIB-OUT list, if any. 
For ECMP case, BGP sends route with list of nexthops to Zebra for programming. In fpmsyncd, as per the route table schema, the route is received with a list of nexthops. If the nexthop group programming fails, it is treated as route add failure in BGP.
If the error-handling feature is disabled, fpmsyncd does not receive any notification from ERROR_ROUTE_TABLE.
## 3.2 DB Changes
### 3.2.1 CONFIG DB
A new table BGP_ERROR_CFG_TABLE has been introduced in CONFIG DB (refer section 3.7).
### 3.2.2 APP DB
### 3.2.3 STATE DB
### 3.2.4 ASIC DB
### 3.2.5 COUNTER DB

## 3.3 FRRouting Design
### 3.3.1 Zebra changes
Zebra, on receiving the message containing route install success, will notify BGP so that it can advertise the route to its peers.
Zebra, on receiving the message containing failed route notification, will withdraw the route from kernel. It will also mark the route with flag as "Not installed in hardware" and store the route. It will not send the next best route to fpmsyncd. At this stage, route is present in Zebra. It will NOT notify BGP of the route add failure.

### 3.3.2 BGP changes
When BGP learns a route, it marks the route as "pending FIB install" and sends the route to Zebra. The route may or may not be successfully installed in hardware.  On receiving route add sucess notification message, BGP will remove the "pending FIB install" flag and advertise the route to its peers. 

In case user wants to retry the installation of failed routes, he/she can issue the command in Zebra. The command will reprogram the failed route in kernel and send that route to hardware.  If the route is successfully programmed in hardware, it will notify Zebra. Zebra will, in turn, notify BGP and route will be advertised to its neighbors.

## 3.4 SwSS Design

### 3.4.1 fpmsyncd changes
A new class is added in fpmsyncd to subscribe to ERROR_ROUTE_TABLE present inside the ERROR_DB.  Subscription to this table is sufficient to handle the errors in route installation.
Currently, fpmsyncd has a TCP socket with Zebra listening on FPM_DEFAULT_PORT. This socket is used by Zebra to send route add/delete related messages to fpmsyncd. We will reuse the same socket to send information back to Zebra. 
fpmsyncd will convert the ERROR_ROUTE_TABLE entry to Zebra common header format and send the message. Zebra will send a delete route message to clean the route from APP_DB so that OrchAgent can process it. If processing this results in a further error, then fpmsyncd silently ignores this.

## 3.5 SyncD

## 3.6 SAI


## 3.7 CLI
### 3.7.1 Data Models
A new table is added in CONFIG_DB to enable and disable error_handling feature.
BGP_ERROR_CFG_TABLE
```
key  					= BGP_ERROR_CFG_TABLE:config
```
The above key has field-value pair as {"enable", "true"/"false"} based on configuration.
### 3.7.2 Configuration Commands
A command is provided in SONIC to enable or disable this feature. 

```
root@sonic:~# config bgp error-handling --help
Usage: config bgp error-handling [OPTIONS] COMMAND [ARGS]...

  Handle BGP route install errors

Options:
  --help  Show this message and exit.

Commands:
  disable  Administratively Disable BGP error-handling
  enable   Administratively Enable BGP error handling
  ```
  When the error-handling is disabled, fpmsyncd will not subcribe to any notification from ERROR_ROUTE_TABLE.  By default, the error-handling feature is disabled. During system reload, config replay for this feature is possible when the docker routing config mode is unified or split.
 This feature can be turned off on demand. But it can affect the system stability. When the config was turned on, there may be some routes in BGP, for which, it is waiting for update from hardware. When the feature is turned off, we will unsubscribe from ERROR_DB and will no longer receive any notifications from hardware. Hence, some of the routes may not receive any notification from hardware.  
It is recommended to restart the BGP docker when the config state is changed to disable from enable. By default, this config is disabled. If the config is changed from disable to enable, we do not need to restart the docker. But the feature will be affecting only those routes which will be learnt after enabling the feature.
  
### 3.7.3 Show Commands
```
sonic(config-router-af)# do show bgp ipv4 unicast 
BGP table version is 1, local router ID is 10.1.0.1, vrf id 0
Status codes:  s suppressed, d damped, h history, * valid, > best, = multipath,# FIB install pending.
               i internal, r RIB-failure, S Stale, R Removed
Nexthop codes: @NNN nexthop's vrf id, < announce-nh-self 
Origin codes:  i - IGP, e - EGP, ? - incomplete

   Network          Next Hop            Metric LocPrf Weight Path
*># 21.21.21.21/32   4.1.1.2                  0             0 101 ?

Displayed  1 routes and 1 total paths  
 ``` 
  
  
  

```
sonic(config-router-af)# do show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR,
       > - selected route, * - FIB route, # - Not installed in hardware

K>* 0.0.0.0/0 [0/0] via 10.59.128.1, eth0, 09:44:37
C>* 4.1.1.0/24 is directly connected, Ethernet4, 00:01:48
C>* 10.1.0.1/32 is directly connected, lo, 09:44:37
C>* 10.59.128.0/20 is directly connected, eth0, 09:44:37
B># 21.21.21.21/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:07
```
A new command has been introduced for seeing the failed routes as follows  
  show {ip | ipv6} route not-installed [prefix/mask]
```
sonic# show ip route not-installed
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR,
       > - selected route, * - FIB route # - not installed in hardware
B> # 22.1.1.1/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 22.1.1.2/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.1/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.2/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.3/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.4/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.5/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.6/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.7/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
B> # 30.1.1.8/32 [20/0] via 4.1.1.2, Ethernet4, 00:00:20
```
### 3.7.4 Debug Commands
In order to retry the installation of failed routes from Zebra, a clear command has been provided.  
  clear {ip | ipv6} route {not-installed | <prefix/mask>}
  ```
sonic# clear ip route 
  not-installed  not installed in hardware
sonic# clear ip route not-installed 
  <cr>        
  A.B.C.D/M   ipv4 prefix with mask
  X:X::X:X/M  ipv6 prefix with mask
```
The above command will send route add message for the failed route from Zebra to fpmsyncd. 

### 3.7.5 REST API Support

# 4 Flow Diagrams
 ![BGP](images/bgp_error_handling_flow1.png "Figure 1: High level module interaction for route install error notification")

__Figure 1: High level module interaction for route install error notification__ 

![BGP](images/bgp_error_handling_flow2.png "Figure 2: Module flow for route add error notification")

__Figure 2: Module flow for route add error notification__

![BGP](images/bgp_error_handling_flow3.png "Figure 3: Module flow for route install success notification")

__Figure 3: Module flow for route add success notification__
 ![BGP](images/bgp_error_handling_flow4.png "Figure 4: Module flow for route delete success/fail notification")

__Figure 4: Module flow for route delete success/fail notification__
 
# 5 Serviceability and Debug


# 6 Warm Boot Support
There are two scenarios here. One is warm-reboot case and another is unplanned reboot (like bgp restart or docker restart due to cold reboot).  Note that in current sonic code, we don't retain routes learnt by Zebra across
warm-reboot. 
During warm reboot, fpmsyncd supports syncing of existing routes in APP_DB with newly learnt routes.  After warm reboot of BGP docker, BGP sends newly learnt routes to fpmsyncd. Since warm reboot is enabled, fpmsyncd will mark the existing db routes and send only the newly learnt routes to APP_DB. If BGP error-handling is enabled, for the routes which were same as before, we will send an implicit positive ACK to Zebra. 
Before warm reboot, suppose, we had 5 routes sent by BGP to fpmsynd, out of them., 5th route failed to be installed in hardware. Zebra will delete the 5th route from kernel, APP_DB, ASIC_DB and ERROR_DB. After warm reboot, when fpmsyncd receives the 5 routes again from BGP, it will send add for the 5th route again (since 5th route was never present in APP_DB prior to warm reboot).
During unplanned reboot, for the same 5 routes, suppose, fpmsyncd crashed before processing the add failure for the 5th route. Now, all the 5 routes are present in APP_DB and ASIC_DB. Since 
the 5th route failed to be installed in hardware, it is present in ERROR_DB. When docker comes up again, orchagent will send the notification for the 5th route failure to fpmsyncd. fpmsyncd will send this message to Zebra. Zebra cleans the route from APP_DB and ASIC_DB. After the warm reboot timer expires, fpmsyncd will
receive the implicit ACK for the remaining routes (routes which did not change during warm-reboot). If any route changes during warm-reboot, the route will be sent to orchagent for installation in hardware and ACK will take its normal flow.

# 7 Scalability

# 8 Unit Test

The UT testcases are as follows:

|**Test-Case ID**|**Description**|**Status**|**Comments**|  
|----------------|---------------|----------|------------|
1           | Send an   iBGP route from the traffic generator and see that route is learnt in   BGP.                                                                                                                                                                                                                                                           |        | Check   the route in zebra. fpmsyncd should send route to APP_DB. Check APP_DB. Check   that orchagent should send this route to ASIC_DB. Check      that syncd should send the route to ASIC. |
 2           | Send an   eBGP route from the traffic generator and see that route is learnt in   BGP.                                                                                                                                                                                                                                                           |        |                                                                                                                                                                                                |
 3           | Install   a route and check that error status is present in "show ip route"   in zebra.                                                                                                                                                                                                                                                          |        |                                                                                                                                                                                                |
 4           | Install   a route and check that route is present in kernel.                                                                                                                                                                                                                                                                                     |        |                                                                                                                                                                                                |
 5           | Install   a route and check that route is present in APP_DB and ASIC_DB.                                                                                                                                                                                                                                                                         |        |                                                                                                                                                                                                |
 6           | Execute   the command "show bgp ipv4". Check that the error status (installed   in hardware flag) is shown as 0.                                                                                                                                                                                                                                 |        |                                                                                                                                                                                                |
 7           | Check   that routes with installed flag as TRUE is sent to eBGP peers. Also, BGP   ribout list should have this route.                                                                                                                                                                                                                           |        |                                                                                                                                                                                                |
 8           | Check   that routes with installed flag as TRUE is sent to iBGP peers. (Rules for   iBGP and route reflector will apply).                                                                                                                                                                                                                        |        |                                                                                                                                                                                                |
 9           | Send an   iBGP route from the traffic generator and see that route is learnt in BGP.   But this route is not installed in ASIC_DB. Check that error status is   correctly shown in APP_DB.      Please note that route will be present in BGP/Zebra/APP_DB.                                                                                      |        | Check   the route in zebra. fpmsyncd should send route to APP_DB. Check APP_DB. Check   that orchagent should send this route to ASIC_DB. Check      that syncd should send the route to ASIC. |
 10          | Send an   eBGP route from the traffic generator and see that route is learnt in BGP.   But this route is not installed in ASIC_DB. Check that error status is   correctly shown in APP_DB.      Check different kinds of errors like nexthop group-id add failed, nexthop   add failed, route add failed, route table/nexthop table is full etc. |        |                                                                                                                                                                                                |
 11          | Install   a route and check that route is present in zebra, but not in ASIC_DB and   kernel.                                                                                                                                                                                                                                                     |        |                                                                                                                                                                                                |
 12          | Install   a route and check that route is not present in APP_DB and ASIC_DB. (Can be   due to send error from fpmsyncd).                                                                                                                                                                                                                         |        |                                                                                                                                                                                                |
 13          | Execute   the command "show bgp ipv4". Check that the error status (installed   flag) is shown as some non-zero value. Also check the rib failure flag. In   case of error, check if BGP ribout message does not contain this route.                                                                                                             |        |                                                                                                                                                                                                |
 14          | Check   that routes with installed flag as FALSE is not sent to eBGP peers. Also, BGP   ribout list should not have this route. If route has already been sent by   BGP, it should be withdrawn.                                                                                                                                                 |        |                                                                                                                                                                                                |
 15          | Check   that routes with installed flag as FALSE is not sent to iBGP peers. (Rules   for iBGP and route reflector will apply). If route has already been sent by   BGP, it should be withdrawn.                                                                                                                                                  |        |                                                                                                                                                                                                |
 16          | Send a   route. Execute "show bgp ipv4". Check that this command shows the   error status (installed flag).  See   that it shows error.  Also, check the   rib-failure flag.                                                                                                                                                                     |        |                                                                                                                                                                                                |
17          | Send a   route. Execute "show bgp ipv4". Check that this command shows the   error status (installed flag).  See   that it shows error.  Also, check the   rib-failure flag. Now,send the same route again so that it in installed successfully. Check all the flags.                                                                                                                                                                     |        |                                                                                                                                                                                                |
# 9 Internal Design Information