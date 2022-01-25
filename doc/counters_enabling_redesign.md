# Counters Enabling Redesign

## Table of Content

* [Revision](#revision)
* [Overview](#overview)
* [Requirements](#requirements)
* [High-Level Design](#high-level-design)
* [Open Question](#open-question)


### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |  12.15.2021 | Noa Or             | Initial version                   |


## Overview

In the current design of counter enabling, when enable_counters.py script is triggered, if the switch uptime is less then 5 minutes, it sleeps for 3 minutes. If not, sleep for 1 minute. This is done in order to make sure the system is up and synchronized.

The purpose of counters redesign is to change the 'sleep' mechanism to be event driven and to have the exact time when the switch is ready to enable counters.
In addition, enable_counters.py script will be removed, and its logic will now be in FlexCounterOrch.

## Requirements

Remove enable_counters.py script and merge the logic into FlexCounterOrch.
FlexCounterOrch will wait for system to be stable using events from APP DB, then enable the counters using the logic written in enable_counters.py.

We will consider the system as stable when all ports and LAGs are in their expected state taken from CONFIG DB, and all BGP neighbors have been learned. 


## High-Level Design

FlexCounterOrch daemon will be refactored to do the following:

- Query admin_status for each port from config_db - PORTCHANNEL & PORT tables.

- Create an internal data structure that will contain:

    { port: [admin_status, oper_status] }
    for all ports and LAGs exist in config_db. oper_status will be initialized as an empty string.

- Create an internal data structure that will conatin all BGP neighbors (IPv4 & IPv6), with IP neighbors we expect to have on the corresponding port/LAG. 

    - Check in BGP_NEIGHBOR table in CONFIG DB which neighbor IP we expect to have as part of NEIGH_TABLE for the local port and keep the ip for the next step. 
    
    - Check in 'INTERFACE', 'PORTCHANNEL_INETRFACE' tables in CONFIG_DB which of the ports & LAGs have an IP address saved in the previous step.


    - Add to the internal data structure the port/LAG with the expected neighbor. 

        For example, 

        In BGP_NEIGHBOR table we check the local_addr IP for 10.0.0.57 neighbor. 
        ```
        127.0.0.1:6379[4]> hgetall BGP_NEIGHBOR|10.0.0.57
        1) "admin_status"
        2) "down"
        3) "asn"
        4) "64600"
        5) "holdtime"
        6) "10"
        7) "keepalive"
        8) "3"
        9) "local_addr"
        10) "10.0.0.56"
        11) "name"
        12) "ARISTA01T1"
        13) "nhopself"
        14) "0"
        15) "rrclient"
        16) "0"

        ```

        In Config DB PortChannel101 has 1.0.0.56 IP address. 
        ```
        PORTCHANNEL_INTERFACE|PortChannel101|10.0.0.56/31
        ```

        The new data structure will contain:
        ```
        {PortChannel101, 10.0.0.57}
        ```

- Start listen to events from APP DB - PORT_TABLE, LAG_TABLE.

    For each event arriving:
    - If PORT table doesn't have "PortConfigDone" key, delete the event and continue to the next one.
    - If the current oper_status of the port equals to the expected, remove the port from the internal list.
    - Otherwise, continue.

- Listen to events from APP DB - NEIGH_TABLE.
    For each event arriving:
    - If a pair from the above neighbor data structure appears in the table, remove it from the list.
    In the above example:
        ```
        NEIGH_TABLE:PortChannel101:10.0.0.57
        ```

- In order to handle changes of changing port's state, or using DPC capabilities,
    listen to events from config_db, PORT & PORTCHANNEL tables.
    for each event arriving:

    - If a port state has been changed, change it in the internal data structure.
    - If a port/portchannel was added, add it to the internal data structure with the proper admin status and empty string in oper status. 
    - If a delete operation was performed to one of the ports inside the internal data structure - remove the port.


    Eventually, when the ports list  and neighbors list are empty, enable the counters. 
    

- The daemon will also create a timer in order to be able to enable counters even if one of the ports is not stable.
    
    As enable_counters.py script, if the system is after reboot (uptime < 5 minutes), the timer will be set to 3 minutes. 
    Else, the timer will be set to 1 minute. 
    
    If after the timer has expired, the counters were not enabled yet, enable counters.

    When doTask(SelectableTimer*) function will be triggered, it will check if the counters are already enabled.
    If not, enable them.



In warm reboot scenario, flexCounterOrch will only listen to warm reboot finalizer indicator and then enable the counters. 

## Open Question

In Current FlexCounterorch design, the `FLEX_COUNTER_DELAY_STATUS` flag is an indicator in CONFIG DB for counters enabling delay. 

When we execute fast-boot, `FLEX_COUNTER_DELAY_STATUS` is set to `true`.
- In FlexCounterOrch, we will not enable the counters until `FLEX_COUNTER_DELAY_STATUS` is `false` (or does not exist at all).

- In enable_counters.py script, after the delay timer is expired, we change the `FLEX_COUNTER_DELAY_STATUS` to `false` and start enabling the counters.


In this design change we have 2 options:

1. Keep using `FLEX_COUNTER_DELAY_STATUS`. It will keep delaying counters only for fast-boot.

2. Remove `FLEX_COUNTER_DELAY_STATUS`. In that case, all boot types will be forced to use a delay, and FlexCounetrOrch will now ignore all events from CONFIG_DB, until counters were enabled (boolean from new design equals true).
