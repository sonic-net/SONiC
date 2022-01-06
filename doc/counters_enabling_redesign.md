# Counters Enabling Redesign

## Table of Content

* [Revision](#revision)
* [Overview](#overview)
* [Requirements](#requirements)
* [High-Level Design](#high-level-design)


### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |  12.15.2021 | Noa Or             | Initial version                   |


## Overview

In the current design of counter enabling, when enable_counters.py script is triggered, if the switch uptime is less then 5 minutes, it sleeps for 3 minutes. This is done in order to make sure the system is up and synchronized.

The purpose of counters redesign is to change the 'sleep' mechanisem to be event driven and to have the exact time when the switch is ready to enable counters.
In addition, enable_counters.py script will be removed, and its logic will now be in flexCountersOrch.

## Requirements

Remove enable_counters.py script and merge the logic into FlexCountersOrch.
FlexCountersOrch will wait for system to be up using events from APP DB, then enable the counters using the logic written in enable_counters.py.

## High-Level Design

FlexCountersOrch daemon will be refactored to do the following:

- Query admin_status for each port from config_db - PORTCHANNEL & PORT tables.

- Create an intenral data structure that will contain:

    { port: [admin_status, oper_status] }
    for all ports received from config_db. oper_status will be initialized as an empty string.

- Start listen to events from APP DB, PORT_TABLE, LAG_TABLE.

    For each event arriving:
    - If Port table doesn't have "PortConfigDone" key, delete the event and continue to the next one.
    - If the current oper_status of the port equals to the expected, remove the port from the list.
    - Otherwise, continue.

- In order to handle changes of changing port's state, or using DPC capabilities,
    listen to events from config_db, PORT & PORTCHANNEL tables.
    for each event arriving:

    - If a port state has been changed, change it in the internal data structure.
    - If a port/portchannel was added, add it to the internal data structure with the proper admin status.
    - If a port/portchannel was deleted, remove it from the internal data structure.
    - If a delete operation was performed to one of the ports inside the internal data structure - remove the port.

Eventually, when the list is empty, enable the counters.

- The daemon will also start a timer in order to be able to enable counters even if one of the ports is not stable.
If after 3 minutes (180 seconds), the counters were not enabled yet, enable counters.

    The timer will be running in a thread doing the following:

    - Initialize a wait_time to 180 seconds.
    - Sleep 10 seconds.
    - Check if the counters were already enabled using a common boolean.
        - If boolean == True, stop running.
        - else, continue with loop.

    - If after 3 minutes the boolean == False, enable counters.
