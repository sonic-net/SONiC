# Config reload Enhancement #

## Table of Content

- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#definitionsabbreviations)
- [Overview](#overview)
- [Requirements](#requirements)
- [High-Level Design](#high-level-design)
- [SAI API Requirements](#sai-api-requirements)
- [Configuration and management ](#configuration-and-management)
    - [Config command](#config-command)
    - [Show command](#show-command)
- [YANG Model changes](#yang-model-changes)
- [Warmboot and Fastboot Considerations](#warmboot-and-fastboot-considerations)
- [Testing Design](#testing-design)
    - [Unit Tests](#unit-tests)
    - [System tests](#system-tests)


### Revision

 | Rev |     Date    |       Author        | Change Description                         |
 |:---:|:-----------:|:-------------------:|--------------------------------------------|
 | 0.1 |             |      Sudharsan      | Initial version                            |

### Scope
This document is the design document for enhancing the config reload in SONiC.

### Definitions/Abbreviations
 

### Overview
In the existing SONiC architecture, when config reload command is executed, it restarts all services by restarting the sonic.target using systemctl. This will result in all the daemons that are associated with sonic.target restart at the same time based on the sequencing defined in the systemd files. Due to this there will be a high contention of CPU and this would delay the switch initialization and subsequent ports creation. Due to this approach the below logs are seen during config reload which gives a false impression of switch taking more time to initialize.
```
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- threadFunction: time span WD exceeded 30955 ms for create:SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- logEventData: op: create, key: SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_INIT_SWITCH: true
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_FDB_EVENT_NOTIFY: 0x55dabccda690
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_PORT_STATE_CHANGE_NOTIFY: 0x55dabccda6a0
Feb 8 21:13:46.695474 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY: 0x55dabccda6b0
Feb 8 21:13:46.695525 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_SWITCH_SHUTDOWN_REQUEST_NOTIFY: 0x55dabccda6c0
Feb 8 21:13:48.653822 sonic ERR syncd#SDK: :- setEndTime: event 'create:SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000' took 32913 ms to execute
Feb 8 21:13:48.654048 sonic ERR syncd#SDK: :- logEventData: op: create, key: SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000
Feb 8 21:13:48.654230 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_INIT_SWITCH: true
Feb 8 21:13:48.654405 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_FDB_EVENT_NOTIFY: 0x55dabccda690
Feb 8 21:13:48.654971 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_PORT_STATE_CHANGE_NOTIFY: 0x55dabccda6a0
Feb 8 21:13:48.655165 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY: 0x55dabccda6b0
Feb 8 21:13:48.655338 sonic ERR syncd#SDK: :- logEventData: fv: SAI_SWITCH_ATTR_SWITCH_SHUTDOWN_REQUEST_NOTIFY: 0x55dabccda6c0
```
This problem is solved during the reboot by selectively delaying non critical services like snmp, telemetry, etc,. using systemd timers with fixed delay. This approach is not event driven and may not be optimal during config reload.
In this new design, the non critical services will be started only after the ports are initialized using an event driven approach.

### Requirements

Primary requirements for sequencing the config reload are
- Immediately restart the critical services during config reload.
- The non critical services are not started. They should be started only after all the ports are initialized.
- Provide a fallback option to restart the services after a fixed internal. This should be the same as in existing reboot flow.
- The existing reboot flows - warm, fast and cold shouldn't be impacted by this enhancement.


### High-Level Design
Currently hostcfgd controls the services based on the feature table. The feature table has a specific field 'has_timer' for the non essential services which needs to be delayed during the reboot flow. The services associated with these features are skipped to activated and only their timers are activated which will later activate these features based on the delay. In the new design apart from activing the timers, hostcfgd will also cache these delayed services. The hostcfgd will also subscribe to PORT_TABLE in the APPL_DB. Once the switch is initialized and all the ports are created in ASIC and Kernel the PortSyncd will publish PortInitDone key in the APPL_DB. On receiving this key the hostcfgd will go through the delayed services list and enables them.
By having the timers intact this approach will ensure there is a backup timer which will activate the services in case after a fixed internal in case of a failure in hostcfgd.
Currently all the timers have 'OnBootSec' which is used as a delay from boot time. This needs to be modified to 'OnActiveSec' which is meant to delay from the time the timer was activated.
The below diagram explains the sequence when config reload is executed. 
![](/images/config_reload/Enhance_config_reload.JPG)
The below diagram explains the new sequence inside hostcfgd.
![](/images/config_reload/Hostcfgd_flow_for_delayed_services.JPG)
### SAI API Requirements
None

### Configuration and management

#### Config command

No new commands are introduced as part of this design.

#### Show command

No new commands are introduced as part of this design
### YANG model changes

No CONFIG_DB fields are modified as part of this design.

### Warmboot and Fastboot Considerations

Unlike the existing flow where services are delayed for a fixed time during fastboot, in the new flow it will be event driven and the delayed services would start once the ports are initialized. However this shouldn't impact the existing fastboot flow. The new design will be tested against the fastboot benchmark tests to ensure no new degradation is introduced because of this event driven approach

### Testing Design

#### Unit tests
Hostcfgd tests would be enhanced to cover the new flow.
- Ensure the service start are done for critical services immediately without delay.
- Ensure the service start for timers are programmed immediately for delayed services.
- Ensure the delayed services are started as soon as PortInitDone is seen in APPL_DB table

#### System tests
There are existing SONiC mgmt tests to cover config reload scenario. After this feature the existing tests should run without degradation. The only noticable differentiation is the switch would be initialized faster in the new flow compared to the existing flow.


