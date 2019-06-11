# L3 Scaling and Performance Enhancements
Layer 3 Scaling and Performance Enhancements
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
| Rev   | Date          | Author               | Change Description                  |
| :---: | :-----------: | :------------------: | ----------------------------------- |
| 0.1   | 06/04/2019    | Arvind               | Initial version                     |
|       |               |                      |                                     |

# About this Manual
This document provides information about the Layer 3 performance and scaling improvements done in SONiC 201908.
# Scope
This document describes the high level design of Layer 3 performance and scaling improvements.

# 1 Requirement Overview
## 1.1 Functional Requirements

 - __Scaling improvements__
    1. ARP/ND 
	     - Support for 32k IPv4 ARP entries
	     - Support for 16k IPv6 ND entries
    2. Route scale
       - 200k IPv4 routes
       - 65k IPv6 routes

    3. ECMP
       - 512 groups X 32 paths
       - 256 groups X 64 paths
       - 128 groups X 128 paths
      
       The route scale and ECMP items mentioned above will be tested to success.
       A Broadcom Tomahawk-2 platform will be used for this testing, but the focus is on SONiC behavior
       
 - __Performance improvements__
 
   4. Reduce the IPv4 and IPv6 route programming time
   5. Reduce unknown ARP/ND learning time
   6. Reduce the time taken to display output with the following *"show commands"*
      - **_show arp_**
      - **_show ndp_**
     
     

## 1.2 Configuration and Management Requirements
No new configuration or show commands introduced.

## 1.3 Scalability Requirements
Covered in Functional requirements


## 1.4 Warm Boot Requirements

There are no specific changes done for Warm-boot in this feature, however  testing will done to make sure no change affect the warm boot time. 

# 2 Design

## 2.1 Scaling improvements

### 2.1.2 Improvement in number of ARP Entries

SONiC currently supports around 2400 host entries.

In our testing we found, when sending a lot of ARP/ND requests in a burst, ARP entries are getting purged from the kernel while the later set of ARP entries was still getting added.
The sequence of add/remove is in such a way that we were never able to cross ~2400 entries .

In the kernel ARP module the following attributes govern how many ARP entries are key in the Kernel ARP cache
```
gc_thresh1 (since Linux 2.2)
The minimum number of entries to keep in the ARP cache. The garbage collector will not run if there are fewer than this number of entries in the cache. Defaults to 128.

gc_thresh2 (since Linux 2.2)
The soft maximum number of entries to keep in the ARP cache. The garbage collector will allow the number of entries to exceed this for 5 seconds before collection will be performed. Defaults to 512.

gc_thresh3 (since Linux 2.2)
The hard maximum number of entries to keep in the ARP cache. The garbage collector will always run if there are more than this number of entries in the cache. Defaults to 1024.
```

To increase the number of ARP/ND entries these attributes will be changed to following values for IPv4 and IPv6
```
net.ipv4.neigh.default.gc_thresh1=16000
net.ipv4.neigh.default.gc_thresh2=32000
net.ipv4.neigh.default.gc_thresh3=48000

net.ipv6.neigh.default.gc_thresh1=8000
net.ipv6.neigh.default.gc_thresh2=16000
net.ipv6.neigh.default.gc_thresh3=32000
```
To increase rate of the ARP/ND packets coming to the CPU. Currently the max rate for ARP/ND is 600 packets, we will be increasing it to higher number(8000) in CoPP file  to improve the learning time.

## 2.2 Performance Improvements

This section elaborates the changes done to improve L3 performance in SONiC

### 2.2.1 Route installation time

The tables below captures the baseline route programming time for  IPv4 and IPv6 prefixes in SONiC.
To measure route programming time, BGP routes were advertised to a SONiC router and timed how long it took for these routes to be installed in the ASIC.

### Table 2: IPv4 prefix route programming time

| Routes                  | time taken on AS7712(Tomahawk) |
| ----------------------- | ------------------------------ |
| 10k IPv4 prefix routes  | 11 seconds                     |
| 30k IPv4 prefix routes  | 30 seconds                     |
| 60k IPv4 prefix routes | 48 seconds                     |
| 90k IPv4 prefix routes  | 68 seconds                     |



### Table 3: IPv6 prefix route programming time

| Routes                             | time taken on AS7712(Tomahawk) |
| ---------------------------------- | -----------------------------  |
| 10k IPv6 route with prefixes > 64b | 11 seconds                     |
| 30k IPv6 route with prefixes >64b  | 30 seconds                     |


#### 2.2.1.1 Proposed optimizations for reducing the route programming time.

- <u>Using sairedis bulk route APIs</u>

  In SONiC architecture, routeorch in Orchagent processes route table updates from the APP_DB and calls the sairedis APIs to put these routes in ASIC_DB. 
  Currently Orchagent processes each route and puts in the ASIC_DB one at a time. The Redis pipelining allows for some level of bulking when putting entries in ASIC_DB but still one DB message is generated for every route.

  Further bulking can be done by using the sairedis bulk APIs for route creation and deletion.

  By using Sairedis bulk APIs, orchagent will call these APIs with a list of routes and their attributes.
  The meta_sai layer in sairedis iterates over this route list and creates the meta objects for every route but only one Redis DB message will be generated for the route list. 
  Therefore using the sairedis bulk APIs reduces the number of Redis messages. 
  
  The ASIC doesn't support bulk route creation/deletion,so syncd still processes one route at time and updates the ASIC.

  So, the saving achieved by using bulk APIs will be number of Redis message generated.

  Bulking of Route updates will be enabled in Orchagent. Orchagent will bulk 64 updates and send to Sairedis. 
  A new timer will be introduced in orchagent to flush the outstanding updates every second.

- <u>Optimization in Fpmsyncd</u>

  Fpmsyncd listens to Netlink messages for Route add/delete messages and updates the APP_DB.
  Current behaviour in Fpmsyncd
   - When fpmsyncd get a route first it tries to get the master device name from the rt_table attribute of route object.
     This is done to check if the route belongs to VNET_ROUTE_TABLE.
  - To get a Master device name, fpmsyncd does a lookup in its local link cache. 
  - If the lookup in the local link cache fails, fpmsyncd updates cache by getting the configured links from the kernel.
  
  The problem here is if there are no VNET present on the system, this lookup will always fail and cache is updated for every route.
  This seems to slow down the rate which route programed for the global route table. 
  
  To fix this we will skip the lookup for the Master device name if the route object table value is zero .i.e. the route needs to put in the global routing table
  
  In our testing, we found which this change time taken to add 10k routes to the APP_DB was reduced from 7-8 seconds to 4-5 seconds.

- <u>Optimization in the sairedis</u>.

  In sairedis every sai object is serialized in JSON format while creating the meta sai objects and updating the ASIC_DB.  For serializing it uses json dump functionality to convert the objects in JSON. format. 
  This json dump function is provided by a open source JSON library. [[link to the open-source project](https://github.com/nlohmann/json)]

  Currently SONiC uses version 2.0 of this library, latest version however is version 3.6.1
  There have a been a few bug fixes/improvements done to the *dump()* from v 2.0 to v 3.6.
  
  We will be upgrading this library to latest version to pick up all the fixes.


With the above mentioned optimizations we target to get 30% reduction in the route programming time in SONiC.

### 3.3 show CLI command enchancements

#### 3.3.1 show arp/ndp command improvement.

The current implemetation of the cli script for "show arp" or "show ndp" fetches the whole FDB table to get the outgoing interface incase the L3 interface is a VLAN L3 Interface. 

This slows down the show command. We will make changes to the CLI script to get FDB entries only for this specific ARP/ND instead of getting the whole FDB table. 

These changes will improve the performance of the command significantly

# 4 Warm Boot Support
No specific changes are planned for Warm boot support as these are exisiting features.

However, testing will done to make sure the changes done, for scaling or performance improvements, won't affect the Warm boot functionality. 



# 5 Unit Test
## 5.1 IPv4 Testcases
| Testcase number | Testcase                                                                      | Result | Time taken |
| --------------- | ----------------------------------------------------------------------------- | ------ | ---------- |
|              1. | Verify  10k IPv4 routes are installed and measure the route programming time  |        |            |
|              2. | Verify 60k IPv4 routes are installed  and measure the route programming time  |        |            |
|              3. | Verify 90k IPv4 routes are installed  and measure the route programming time  |        |            |
|              4. | Verify 128k IPv4 routes are installed and measure the route programming time  |        |            |
|              5. | Verify 160k IPv4 routes are installed  and measure the route programming time |        |            |
|              6. | Verify 200k IPv4 routes are installed and measure the route programming time  |        |            |
|              7. | Verfiy  8k IPv4 ARP entries are learnt and measure the learning time          |        |            |
|              8. | Verify  16k IPv4 ARP entries are learnt and measure the learning time         |        |            |
|              9. | Verify  32k IPv4 ARP entries are learnt and measure the learning time         |        |            |
## 5.2 IPv6 Testcases
| Testcase number | Testcase                                                                                       | Result | Time taken |
| --------------- | ---------------------------------------------------------------------------------------------- | ------ | ---------- |
|              1. | Verify 10k IPv6 routes with prefix >64b  are installed  and measure the route programming time |        |            |
|              2. | Verify 25k IPv6 routes with prefix > 64b are installed and measure the route programming time  |        |            |
|              3. | Verify 40k IPv6 routes with prefix > 64b are installed and measure the route programming time  |        |            |
|              4. | Verfiy  8k IPv6 ND entries are learnt and measure the learning time                            |        |            |
|              5. | Verify  16k IPv6 ND entries are learnt and measure the learning time                           |        |            |
|                 |                                                                                                |        |            |
## 5.3 Regresssion Testcases
| Testcase number | Testcase                                                    | Result | Time taken |
| --------------- | ----------------------------------------------------------- | ------ | ---------- |
|              1. | Measure the convergence time with link flaps                |        |            |
|              2. | Measure the convergence  time with Link flaps on ECMP paths |        |            |
|              3. | Clear bgp neighbors to check all routes and forwarding      |        |            |
|              4. | Clear neigh table and check all routes and forwarding       |        |            |
|              5. | Clear mac table and check all routes and forwarding         |        |            |
|              6. | Test across warm reboot , Orchagt/Syncd restart and upgrade |        |            |
 

