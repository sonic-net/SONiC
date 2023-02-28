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
    - [DB Migrator](#db-migrator)
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
- The non critical should be started only after all the ports are initialized.
- Services can be configured to be started immediately or delayed. This can be using a field in FEATURE table.
- The existing timers should be removed by this event driven approach.
- This flow is applicable in case of all reboots (warm/fast/cold) as well as config reload.


### High-Level Design
Currently hostcfgd controls the services based on the feature table. The feature table has a specific field 'has_timer' for the non essential services which needs to be delayed during the reboot flow. This field will be now replaced by new field called "delayed". These services will controlled by hostcfgd.
During the hostcfgd initialization it will cache these delayed services based on the configuration in the feature table. The hostcfgd will also subscribe to PORT_TABLE in the APPL_DB. Once the switch is initialized and all the ports are created in ASIC and Kernel the PortSyncd will publish PortInitDone key in the APPL_DB. On receiving this key the hostcfgd will go through the delayed services list and enables them. There will also be a timeout defined for the services to start if PortInitDone is not defined within the specific timeout. This is to ensure the management related services start even if there is some failure for the switch to initialize.


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

#### DB Migrator

The 'has_timer' field in FEATURE table will be changed to 'delayed'. Hence db_migrator is required to modify the configurations to reflect this change.

### YANG model changes

Yang model needs to be updated for FEATURE_TABLE. The 'has_timer' field will be removed and replaced with 'delayed'

```
                leaf delayed {
                    description "This configuration identicates if the feature needs to be delayed until
                                 system initialization";
                    type stypes:boolean_type;
                    default "false";
                }

```

### Warmboot and Fastboot Considerations

In case of Warmboot and fastboot, Hostcfgd itself is currently delayed today by a timer. This timer will also be removed and replaced by hostcfgd waiting for warmboot/fastboot completion using waitAdvancedBootDone.
Additionally there will be checks added to Warmboot command to ensure all services including delayed services are started before proceeding.

### Testing Design

#### Unit tests
Hostcfgd tests would be enhanced to cover the new flow.
- Ensure the service start are done for critical services immediately without delay. Example services like swss, syncd and bgp.
- Ensure the delayed services are started as soon as PortInitDone is seen in APPL_DB table. Example services includes snmp, lldp and telemetry.

#### System tests
There are existing SONiC mgmt tests to cover config reload scenario. After this feature the existing tests should run without degradation. The only noticable differentiation is the switch would be initialized faster in the new flow compared to the existing flow.


