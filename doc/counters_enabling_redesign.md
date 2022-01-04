# Counters Enabling Redesign

## Table of Content

* [Revision](#revision)
* [Overview](#overview)
* [Requirements](#requirements)
* [High-Level Design](#high-level-design)
    * [Ports Daemon](#ports-daemon)


### Revision

| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |  12.15.2021 | Noa Or             | Initial version                   |


## Overview

In the current design of counter enabling, when enable_counters.py script is triggered, if the switch uptime is less then 5 minutes, it sleeps for 3 minutes. This is done in order to make sure the system is up and synchronized.

The purpose of counters redesign is to change the 'sleep' mechanisem to be event driven and to have the exact time when the siwtch is ready to enable counters.

## Requirements

Change enable_counters.py script to be event driven from config_db instead of using sleeps.


## High-Level Design

### Ports Daemon

enable_counters.py script will be refactored to be running as a daemon.

When system is up after reboot, the new daemon will be created and do the following:

- Query admin_status for each port from config_db - PORTCHANNEL & PORT tables.

- Create an intenral data structure that will contain:

    { port: [admin_status, oper_status] }
    for all ports received from config_db. oper_status will be initialized as an empty string.


- Start listen to events from APP DB, PORT_TABLE, LAG_TABLE.

    For each event arriving:
    - If Port table doesn't have "PortConfigDone" key, delete the event and continue to the next one.
    - If the current oper_status of the port equals to the expected, remove the port from the list.

- In order to handle changes of changing port's state, or using DPC capabilities,

    listen to events from config_db, PORT & PORTCHANNEL tables.
    for each event arriving:
    - If a port state has been changed, change it in the internal data structure.
    - If a port/portchannel was added, add it to the internal data structure with the status.
    - If a port/portchannel was deleted, remove it from the internal data structure.
    - If a delete operation was performed to one of the ports inside the internal data structure - remove the port.

Eventually, when the list is empty, enable the counters.


NOTE: The daemon will also start a timer in order to be able to enable counters even if one of the ports is not stable.
If after 3 minutes (180 seconds), the counters were not enabled yet, enable counters.
The timer will be running in a thread.
