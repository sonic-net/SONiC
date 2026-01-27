# DPU Restart – Solution for database out of sync 
## Problem Statement
When DPU restarts (either as a planned or an unexpected event), DPU_[APPL|STATE] _DB that are hosted on NPU will not be restarted along with DPU. This causes some states to be out of sync and leads to unexpected behaviors in HA scenarios. Today's [SmartSwitch reboot HLD](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/reboot/reboot-hld.md) does not cover database cleanup.

We observed a couple of issues with this problem:
1.	BFD passive sessions (on DPUs) are created once only by hamgrd (when “DPU” table in NPU’s CONFIG_DB is consumed). When DPU is restarted, these BFD sessions are removed and will never be added again. 
2.	DPU_STATE_DB still holds stale entries/values for HA objects. 
3.	Even if we clean up DPU_[APPL|STATE] _DB, NPU’s APPL_DB and STATE_DB will still have stale “HA_SCOPE_CONFIG_TABLE” and “HA_SET_CONFIG_TABLE”.

## Solutions
The following are the proposed actions during DPU reboot.

1. Cleanup `DPU_*_DB` instances when DPU boots up.
1. SDN controller needs to monitor NPU `STATE_DB` entries below: 
    1. `CHASSIS_MODULE_TABLE|DPU<dpu_index>: {'admin_status': 'up|down', 'oper_status': 'up|down'}`  
        This table entry will be updated by [SmartSwitch pmon](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/pmon/smartswitch-pmon.md).
    1. `DPU_RESET_INFO|DPU<dpu_index>: {'reset_status': 'true|false', 'last_reset_status_update': timestamp}`  
        This table will be updated by hamgrd based on `CHASSIS_STATE_DB|DPU_STATE`. Either `dpu_control_plane_state` or `dpu_midplane_link_state` being down will trigger hamgrd to set `reset_status` to `true`.
        Controller will update the status to `false` when it finishes the service provision and HA programming after DPU is up.        
    1.  `DPU_RESET_INFO|DPU<dpu_index>: {'dpu_ready': 'true|false', 'last_dpu_readiness_update': timestamp}`  
        This field indicates if dpu is ready to be provisioned. Hamgrd will set the value to `false` when `dpu_control_plane_state` or `dpu_midplane_link_state` goes down, and set the value back to `true` when the states are up. 
          
1. SDN controller will then   
    1. Delete stale HA_SET_CONFIG and HA_SCOPE_CONFIG  
    1. Re-program DASH objects, HA_SET_CONFIG and HA_SCOPE_CONFIG  
    1. Once services are provisioned, HA is programmed, SDN controller will set `reset_status` to `false` 
1. Hamgrd needs to change the passive BFD session creation logic, today the sessions are created statically. We need this change to avoid hamgrd restart. Hamgrd needs to create BFD session if `dpu_control_plane_state` changes from down to up. 

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
    participant DPU_APPL_DB
    participant DPU_STATE_DB
    participant DPU

    DPU->>DPU: 1. DPU shutdown
    pmon->>NPU CHASSIS_STATE_DB: 2. Update dpu state to down
    hamgrd->>NPU STATE_DB: 3. update local vdpu state in `DASH_HA_SCOPE_STATE` table, update `DPU_RESET_INFO`
    NPU STATE_DB->>SDN Controller: 4. DPU_RESET_INFO|DPU0: {"reset_status": "true", "dpu_ready": "false"}
    hamgrd->>DPU_APPL_DB: 5. hamgrd remove passive BFD sessions
    SDN Controller->>hamgrd: 6. Delete HA_SCOPE_CONFIG and HA_SET_CONFIG
    hamgrd->>DPU_APPL_DB: 7. Delete HA_SET, HA_SCOPE
    hamgrd->>NPU STATE_DB: 8. Delete HA_SCOPE_STATE_TABLE, delete VNet routes.
    DPU->>DPU: 9. DPU boots up 
    DPU->>DPU_APPL_DB: 10. Cleanup Database
    DPU->>DPU_STATE_DB: 11. Cleanup Database
    pmon->>NPU CHASSIS_STATE_DB: 12. Update DPU state to Up
    hamgrd->>DPU_APPL_DB: 13. Create BFD passive sessions. 
    hamgrd->>NPU STATE_DB: 14. DPU_RESET_INFO|DPU0: {"dpu_ready": "true"}

    NPU STATE_DB->>SDN Controller: 15. DPU_RESET_INFO|DPU0: {"dpu_ready": "true"} && CHASSIS_MODULE_TABLE|DPU0 {'admin_status':'up'} &&CHASSIS_MODULE_TABLE|DPU0 {'oper_status':'up'} 


    SDN Controller->>hamgrd: 16. Create DASH objects, HA_SCOPE_CONFIG and HA_SET_CONFIG 
    SDN Controller->>NPU STATE_DB: 17. DPU_RESET_INFO|DPU0: {"reset_status": "false"}
```