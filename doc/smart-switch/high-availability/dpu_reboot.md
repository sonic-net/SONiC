# DPU Restart – Solution for database out of sync 
## Problem Statement
When DPU restarts (either as a planned or an unexpected event), DPU_[APPL|STATE] _DB that are hosted on NPU will not be restarted along with as DPU. This causes some states to be out of sync and leads to unexpected behaviors in HA scenarios. Today's [SmartSwitch reboot HLD](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/reboot/reboot-hld.md) does not cover database cleanup.

We observed a couple of issues with this problem:
1.	BFD passive sessions (on DPUs) are created once only by hamgrd (when “DPU” table in NPU’s CONFIG_DB is consumed). When DPU is restarted, these BFD sessions are removed and will never be added again. 
2.	DPU_STATE_DB still holds stale entries/values for HA objects. 
3.	Even if we clean up DPU_[APPL|STATE] _DB, NPU’s APPL_DB and STATE_DB will still have stale “HA_SCOPE_CONFIG_TABLE” and “HA_SET_CONFIG_TABLE”.

## Solutions
The following are the proposed actions during DPU reboot.

1. Cleanup `DPU_*_DB` instances when DPU boots up.
1. SDN controller needs to monitor NPU `STATE_DB` entries below: 
    1. `CHASSIS_MODULE_TABLE|DPU<dpu_index>: {'admin_status': 'up|down', 'oper_status': 'up|down'}`  
        This table entry will updated by [SmartSwitch pmon](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/pmon/smartswitch-pmon.md).
    1. `DPU_RESET_INFO|DPU<dpu_index>: {'reset_status': 'true|false', 'last_update_timestamp': timestamp}`  
        This table will be updated by hamgrd based on `CHASSIS_STATE_DB|DPU_STATE`. Either `dpu_control_plane_state` or `dpu_midplane_link_state` being down will trigger hamgrd to set `reset_status` to `true`.       
1. SDN controller will then   
    1. Delete stale HA_SET_CONFIG and HA_SCOPE_CONFIG  
    1. Re-program DASH objects, HA_SET_CONFIG and HA_SCOPE_CONFIG  
    1. Once serviecs are provisioned, HA is programmed, SDN control will set `reset_status` to `false` 
1. Hamgrd needs to change the passive BFD session creation logic, today the sessions are created statically. We need this change to avoid hamgrd restart. Hamgrd need to create BFD session if `dpu_control_plane_state` changes from down to up. 

Note that DashHaOrch should cache the BFD session parameters, remove and create the sessions accordingly in planned shutdown. 

## Workflow

```mermaid
sequenceDiagram
    participant SDN Controller
    participant hamgrd
    participant pmon
    participant NPU APPL_DB
    participant NPU STATE_DB
    participant NPU CHASSIS_STATE_DB
    participant DPU_APPL_DB(on NPU)
    participant DPU_STATE_DB(on NPU)
    participant DPU
    participant DashHaOrch

    DPU->>DPU: 1. DPU shutdown
    pmon->>NPU CHASSIS_STATE_DB: 2. Update dpu state to down
    hamgrd->>NPU STATE_DB: 3. update local vdpu state in `DASH_HA_SCOPE_STATE` table, update `DPU_RESET_INFO`
    NPU STATE_DB->>SDN Controller: 4. DPU_RESET_INFO|DPU0: {"reset_status": "true"} || CHASSIS_MODULE_TABLE|DPU0 {'admin_status':'down'} || CHASSIS_MODULE_TABLE|DPU0 {'oper_status':'down'} 
    SDN Controller->>hamgrd: 5. Delete HA_SCOPE_CONFIG and HA_SET_CONFIG
    hamgrd->>DPU_APPL_DB(on NPU): 6. Delete HA_SET, HA_SCOPE
    hamgrd->>NPU STATE_DB: 7. Delete HA_SCOPE_STATE_TABLE
    DPU->>DPU: 8. DPU boots up 
    DPU->>DPU_APPL_DB(on NPU): 9. Cleanup Database
    DPU->>DPU_STATE_DB(on NPU): 10. Cleanup Database
    pmon->>NPU CHASSIS_STATE_DB: 11. Update DPU state to Up
    hamgrd->>NPU STATE_DB: 12. update local vdpu state in `DASH_HA_SCOPE_STATE` table

    NPU STATE_DB->>SDN Controller: 13. DPU_HA_SCOPE_STATE|DPU0: local vdpu states are all up && CHASSIS_MODULE_TABLE|DPU0 {'admin_status':'up'} &&CHASSIS_MODULE_TABLE|DPU0 {'oper_status':'up'} 


    SDN Controller->>hamgrd: 14. Create DASH objects, HA_SCOPE_CONFIG and HA_SET_CONFIG 
    SDN Controller->>NPU STATE_DB: 15: DPU_RESET_INFO|DPU0: {"reset_status": "false"}