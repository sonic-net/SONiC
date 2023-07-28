# Feature Name
Deterministic Approach for Interface Link bring-up sequence

# High Level Design Document
#### Rev 0.7

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Abbreviation](#abbreviation)
  * [References](#references)
  * [Problem Definition](#problem-definition)
  * [Background](#background)
  * [Objective](#objective)
  * [Plan](#plan)
  * [Pre-requisite](#pre-requisite)
  * [Breakout handling](#breakout-handling)
  * [Proposed Work-Flows](#proposed-work-flows)
  * [Port reinitialization during syncd/swss/orchagent crash](#port-reinitialization-during-syncdswssorchagent-crash)

# List of Tables
  * [Table 1: Definitions](#table-1-definitions)
  * [Table 2: References](#table-2-references)

# Revision
| Rev |     Date    |       Author                       | Change Description                  |
|:---:|:-----------:|:----------------------------------:|-------------------------------------|
| 0.1 | 08/16/2021  | Shyam Kumar                        | Initial version                       
| 0.2 | 12/13/2021  | Shyam Kumar,  Jaganathan Anbalagan | Added uses-cases, workflows  
| 0.3 | 01/19/2022  | Shyam Kumar,  Jaganathan Anbalagan | Addressed review-comments    
| 0.4 | 01/26/2022  | Shyam Kumar,  Jaganathan Anbalagan | Addressed further review-comments 
| 0.5 | 01/28/2022  | Shyam Kumar,  Jaganathan Anbalagan | Addressed further review-comments
| 0.6 | 02/02/2022  | Shyam Kumar                        | Added feature-enablement workflow 
| 0.7 | 02/02/2022  | Jaganathan Anbalagan               | Added Breakout Handling 
| 0.8 | 02/16/2022  | Shyam Kumar                        | Updated feature-enablement workflow
| 0.9 | 04/05/2022  | Shyam Kumar                        | Addressed review comments           |


# About this Manual
This is a high-level design document describing the need to have determinstic approach for
Interface link bring-up sequence and workflows for use-cases around it 

# Abbreviation

# Table 1: Definitions
| **Term**       | **Definition**                                   |
| -------------- | ------------------------------------------------ |
| pmon           | Platform Monitoring Service                      |
| xcvr           | Transceiver                                      |
| xcvrd          | Transceiver Daemon                               |
| CMIS           | Common Management Interface Specification        |
| gbsyncd        | Gearbox (External PHY) docker container          |
| DPInit         | Data-Path Initialization                         |
| QSFP-DD        | QSFP-Double Density (i.e. 400G) optical module   |

# References

# Table 2 References

| **Document**                                            | **Location**  |
|---------------------------------------------------------|---------------|
| CMIS v4 | [QSFP-DD-CMIS-rev4p0.pdf](http://www.qsfp-dd.com/wp-content/uploads/2019/05/QSFP-DD-CMIS-rev4p0.pdf) | 
| CMIS v5 | [CMIS5p0.pdf](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf) |


# Problem Definition

1.	Presently in SONiC, there is no synchronization between Datapath Init operation of CMIS complaint optical module and enabling ASIC (NPU/PHY) Tx which may cause link instability during administrative interface enable “config interface startup Ethernet” configuration and bootup scenarios. 
      
    For CMIS-compliant active (optical) modules, the Host (NPU/PHY) needs to provide a valid high-speed Tx input signal at the required signaling rate and encoding type prior to causing a DPSM to exit from DPDeactivated state and to move to DP Init transient state.
      
    Fundamentally it means - have a deterministic approach to bring-up the interface.
      
    Also, this problem is mentioned ‘as outside-the-scope’ of ‘CMIS Application Initialization’ high-level design document
      **(https://github.com/ds952811/SONiC/blob/0e4516d7bf707a36127438c7f2fa9cc2b504298e/doc/sfp-cmis/cmis-init.md#outside-the-scope)**

2.  During administrative interface disable “config interface shutdown Ethernet”, only the ASIC(NPU) Tx is disabled and not the opticcal module Tx/laser. 
      This will lead to power wastage and un-necessary fan power consumption to keep the module temperature in operating range 

# Background

  Per the ‘CMIS spec’,  ‘validation, diagnostics’ done by HW team' and 'agreement with vendors', 
  need to follow following bring-up seq to enable port/interface with CMIS compliant optical modules in LC/chassis:

    a) Enable port on NPU (bring-up port, serdes on the NPU ; enable signals) : syncd
    b) Enable port on PHY (bring-up port, serdes on the PHY ; enable signals) : gbsyncd
       - Wait for signal to stabilize on PHY   
    c) Enable optical module (data path initializatio, turn laser on/ enable tx) : xcvrd

  In boards not having PHY, #b) not needed but #a) and #c) sequence to be followed.
  
  ## Clause from CMIS4.0 spec
  
     Excerpt from CMIS4.0 spec providing detailed reasoning for the above-mentioned bring-up sequence
     
  ![61f5b485-cf3b-4ca8-beac-9102b6feabfe](https://user-images.githubusercontent.com/69485234/147173702-f124fc9d-ef27-4816-b1a1-b4a44a5833a7.PNG)


  ## Clause from CMIS5.0 spec
  
     Excerpt from CMIS5.0 spec providing detailed reasoning for the above-mentioned bring-up sequence
     
  ![96a35dc5-618f-418c-9593-5639a90f1b28](https://user-images.githubusercontent.com/69485234/147173164-5ad0123c-479a-4774-b3ee-12a81fdd7d7e.PNG)
     

# Objective

Have a determistic approach for Interface link bring-up sequence for all interfaces types i.e. below sequence to be followed:
  1. Initialize and enable NPU Tx and Rx path
  2. For system with 'External' PHY: Initialize and enable PHY Tx and Rx on both line and host sides; ensure host side link is up 
  3. Then only perform optics data path initialization/activation/Tx enable (for CMIS complaint optical modules) and Tx enable (for SFF complaint optical modules)

# Plan

Plan is to follow this high-level work-flow sequence to accomplish the Objective:
- xcvrd to subscribe to a new field “host_tx_ready” in port table state-DB
- Orchagent will set the “host_tx_ready” to true/false based on the SET_ADMIN_STATE attribute return status from syncd/gbsyncd. (As part of SET_ADMIN_STATE attribute enable, the NPU Tx is enabled)
- xcvrd process the “host_tx_ready” value change event and do optics datapath init / de-init using CMIS API
- Per the discussion and agreement in sonic-chassis workgroup and OCP community, plan is to follow this proposal for all the known interfaces types- 400G/100G/40G/25G/10G. Reason being: 
  - CMIS complaint optical modules:-
      All CMIS complaint optical modules will follow this approach as recommended in the CMIS spec.
  - SFF complaint optical modules:- 
    - deterministic approach to bring the interface will eliminate any link stability issue which will be difficult to chase in the production network
      e.g. If there is a PHY device in between, and this 'deterministic approach' is not followed, PHY may adapt to a bad signal or interface flaps may occur when the optics tx/rx  enabled during PHY initialization. 
    - there is a possibility of interface link flaps with non-quiescent optical modules <QSFP+/SFP28/SFP+> if this 'deterministic approach' is not followed
    - It helps bring down the optical module laser when interface is adminstiratively shutdown. Per the workflow here, this is acheived by xcvrd listening to host_tx_ready field from PORT_TABLE of STATE_DB. Turning the laser off would reduce the power consumption and avoid any lab hazard
    - Additionally provides uniform workflow (from SONiC NOS) across all interface types with or without module presence. 
  - This synchronization will also benefit SFP+ optical modules as they are "plug N play" and may not have quiescent functionality. (xcvrd can use the optional 'soft tx disable' ctrl reg to disable the tx)

# Pre-requisite

As mentioned above in 'Background' and 'Plan' sections, need to follow specified bring-up sequence.
Work flows are designed considering SONiC NOS operating in sync mode.

In case SONiC NOS operates in async mode, then expected behavior is - the return status of the set ADMIN_STATE attribute update in ASIC-DB (syncd/GBsyncd) will be treated to set the host_tx_ready in Orchagent.

# Breakout Handling
  - The new 'host_tx_ready' field of Port table in state-DB is created for every interface <regular/breakout interface>.
  - Xcvrd processes the 'host_tx_ready' change event and is responsible to disable Tx/laser for all optical lanes or respective optical lane that belongs to the interface in case of breakout.
  - Currently the logical mapping between the interface and optical lane is not present in xcvrd. Creating this logical mapping in xcvrd will address breakout interface handling.

# Proposed Work-Flows

Please refer to the  flow/sequence diagrams which covers the following required use-cases
  - Enabling this feature 
  - Transceiver initialization
  - admin enable configurations 
  - admin disable configurations
  - No transceiver present

# Feature enablement
  This feature (optics Interface Link bring-up sequence) would be enabled on per platform basis.
  There could be cases where vendor(s)/platform(s) may take time to shift from existing codebase to the model (work-flows) described in this document.
  In order to avoid any breakage and ensure gradual migration of different platforms/vendors to this model, will add this new workflow to enable/disable this feature:
  
  In order to enable this feature, the platform would set ‘skip_xcvrd_cmis_mgr’ to ‘false’ in their respective pmon_daemon_control.json as part of platform bootstrap. When xcvrd would spawn on that hwsku (LC/board), it would parse ‘skip_xcvrd_cmis_mgr’ and if found 'false', it would launch CMIS task manager. This implies enabling this feature. 

Else, if ‘skip_xcvrd_cmis_mgr’ is set/found 'true' by xcvrd, it would skip launching CMIS task manager and this feature would remain disabled.
If a platform/vendor does not specify/set ‘skip_xcvrd_cmis_mgr’, xcvrd would exercise the default workflow (i.e. when xcvrd detects QSFP-DD, it would luanch CMIS task manager and initialize the module per CMIS specification). 

Note: This feature flag (skip_xcvrd_cmis_mgr) was added as a flexibility in case vendor/platform intend to disable this feature and not use CMIS task manager. However, techinically, as mentioned in this document, that should not be the case.
  
  Workflow :
  ![Enabling 'Interface link bring-up sequence' feature(2)](https://user-images.githubusercontent.com/69485234/154403945-654b49d7-e85f-4a7a-bb4d-e60a16b826a7.png)



# Transceiver Initialization 
  (at platform bootstrap layer)
  
![LC boot-up sequence - optics INIT (platform bootstrap)](https://user-images.githubusercontent.com/69485234/152261613-e20dcda9-2adc-42aa-a1f1-4b8a47dd32af.png)

# Applying 'interface admin startup' configuration

![LC boot-up sequence - 'admin enable' Config gets applied](https://user-images.githubusercontent.com/69485234/147166867-56f3e82d-1b1c-4b7a-a867-5470ee6050e7.png)


# Applying 'interface admin shutdown' configuration

![LC boot-up sequence - 'admin disable' Config gets applied](https://user-images.githubusercontent.com/69485234/147166884-92c9af48-2d64-4e67-8933-f80531d821b4.png)

# No transceiver present
if transceiver is not present:
 - All the workflows mentioned above will reamin same ( or get exercised) till host_tx_ready field update
 - xcvrd will not perform any action on receiving host_tx_ready field update 

# Port reinitialization during syncd/swss/orchagent crash
## Overview

When syncd/swss/orchagent crashes, all ports in the corresponding namespace will be reinitialized by xcvrd irrespective of the current state of the port.  
If just xcvrd crashes and restarts, then forced reinitialization (CMIS reinit + media settings notify) of port will not be performed.  
Following infra will ensure port reinitialization by xcvrd in case of syncd/swss/orchagent crash:

1. XCVRD main thread init
	- XCVRD main thread creates the key CMIS_REINIT_REQUIRED in PORT_TABLE:\<port\> (APPL_DB) with value as true for ports which do NOT have this key present 
	- XCVRD main thread creates the key MEDIA_SETTINGS_SYNC_STATUS in PORT_TABLE:\<port\> (APPL_DB) with value MEDIA_SETTINGS_DEFAULT for ports which do NOT have this key present.  
      - For transceivers which do not require media settings, MEDIA_SETTINGS_SYNC_STATUS will stay with value MEDIA_SETTINGS_DEFAULT

  Following table describes the various values for MEDIA_SETTINGS_SYNC_STATUS  

|          Value          |                Modifier thread and event               |                                  Consumer thread and purpose                                 |
|:-----------------------:|:------------------------------------------------------:|:--------------------------------------------------------------------------------------------:|
| MEDIA_SETTINGS_DEFAULT  | XCVRD main thread during cold   start of xcvrd         | XCVRD main thread   during boot-up for deciding to notify media settings                     |
|                         | SfpStateUpdateTask during   transceiver removal        |                                                                                              |
| MEDIA_SETTINGS_NOTIFIED | SfpStateUpdateTask while   updating the media settings | Not being used currently                                                                     |
| MEDIA_SETTINGS_DONE     | Orchagent after applying the SI   settings             | CmisManagerTask for proceeding   to CMIS_STATE_DP_DEINIT from CMIS_STATE_MEDIA_SETTINGS_WAIT |

2. SfpStateUpdateTask thread will notify the media settings to OA based on the value of PORT_TABLE:\<port\>.MEDIA_SETTINGS_SYNC_STATUS  
If PORT_TABLE:\<port\>.MEDIA_SETTINGS_SYNC_STATUS != MEDIA_SETTINGS_DONE, notify media settings will be invoked and will be set to MEDIA_SETTINGS_NOTIFIED for a port supporting media settings.
3. The OA upon receiving media settings will
	- Disable port admin status
	- Apply SI settings
	- PORT_TABLE:\<port\>.MEDIA_SETTINGS_SYNC_STATUS = MEDIA_SETTINGS_DONE
4. In the CMIS_STATE_INSERTED state, if 'admin_status' is up and 'host_tx_ready' is true, CmisManagerTask thread will check if
	- the port supports media settings (will be checked using g_dict and finding valid SI values) and
	- MEDIA_SETTINGS_SYNC_STATUS != MEDIA_SETTINGS_DONE  
If all the above conditions are true, CMIS SM transitions to CMIS_STATE_MEDIA_SETTINGS_WAIT state.  
If port doesn't require media settings to be applied, CMIS SM will proceed with normal code flow (transitions to CMIS_STATE_DP_DEINIT)  
Overall, no functionality change related to CMIS SM transitions is intended for ports not supporting media settings
5. CMIS_STATE_MEDIA_SETTINGS_WAIT state will wait for MEDIA_SETTINGS_DONE and upon reaching to MEDIA_SETTINGS_DONE, CMIS SM will transition to CMIS_STATE_DP_DEINIT.  
There will be a timeout of 5s for every retry
6. The CmisManagerTask thread will set “CMIS_REINIT_REQUIRED" to false after CMIS SM reaches to a steady state (CMIS_STATE_UNKNOWN, CMIS_STATE_FAILED, CMIS_STATE_READY and CMIS_STATE_REMOVED) for the corresponding port
7. XCVRD will subscribe to PORT_TABLE in APPL_DB and trigger self-restart if the PORT_TABLE is deleted for the namespace.  
All threads will be gracefully terminated and xcvrd deinit will be performed followed by issuing a SIGABRT to ensure XCVRD is restarted automatically by supervisord. After respawn, CMIS re-init and media_settings notified is triggered for the ports belonging to the affected namespace
8. syncd/swss/orchagent restart clears the entire APPL-DB, including “MEDIA_SETTINGS_SYNC_STATUS” and "CMIS_REINIT_REQUIRED" in PORT_TABLE

## XCVRD init sequence to support port reinitialization during syncd/swss/orchagent crash

```mermaid
sequenceDiagram
    participant APPL_DB
    participant XCVRDMT as XCVRD main thread
    participant CmisManagerTask
    participant SfpStateUpdateTask
    participant DomInfoUpdateTask

    Note over XCVRDMT: Load new platform specific api class,<br> sfputil class and load namespace details
    XCVRDMT ->> XCVRDMT: Wait for port config completion
    loop lport in logical_port_list
        alt if CMIS_REINIT_REQUIRED not in PORT_TABLE:<lport>
            XCVRDMT ->> APPL_DB: PORT_TABLE:<lport>.CMIS_REINIT_REQUIRED = true
        end
        alt if MEDIA_SETTINGS_SYNC_STATUS not in PORT_TABLE:<lport>
            XCVRDMT ->> APPL_DB: PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = MEDIA_SETTINGS_DEFAULT
        end
    end
    Note over APPL_DB: PORT_TABLE:<lport><br>CMIS_REINIT_REQUIRED : true/false<br>MEDIA_NOTIFY_REQUIRED : true/false
    XCVRDMT ->> CmisManagerTask: Spawns
    XCVRDMT ->> DomInfoUpdateTask: Spawns
    XCVRDMT ->> SfpStateUpdateTask: Spawns
    par XCVRDMT, CmisManagerTask, SfpStateUpdateTask, DomInfoUpdateTask
        loop Wait for stop_event else poll every 60s
            DomInfoUpdateTask->>DomInfoUpdateTask: Update TRANSCEIVER_DOM_SENSOR,<br>TRANSCEIVER_STATUS (HW section)<br>TRANSCEIVER_PM tables
        end
        loop Wait for stop_event
            XCVRDMT->>XCVRDMT: Check for changes in PORT_TABLE and act upon receiving DEL event
        end
        Note over CmisManagerTask: Subscribe to CONFIG_DB:PORT,<br>STATE_DB:TRANSCEIVER_INFO and STATE_DB:PORT_TABLE
        loop Wait for stop_event
            Note over CmisManagerTask: Start the CMIS SM and act based on subscribed DB related changes
        end
        Note over SfpStateUpdateTask: _post_port_sfp_info_and_dom_thr_to_db_once<br>_init_port_sfp_status_tbl<br>Subscribe to CONFIG_DB:PORT
        loop Wait for stop_event
            SfpStateUpdateTask ->> SfpStateUpdateTask: Handle config change event<br>retry_eeprom_reading()<br>_wrapper_get_transceiver_change_event
        end
    end
```

## SfpStateUpdateTask's role to notify media settings to OA

```mermaid
sequenceDiagram
    participant OA
    participant APPL_DB
    participant SfpStateUpdateTask

    Note over SfpStateUpdateTask: Subscribe to CONFIG_DB:PORT,<br>STATE_DB:TRANSCEIVER_INFO and STATE_DB:PORT_TABLE
    Note over SfpStateUpdateTask: Following loop represents _post_port_sfp_info_and_dom_thr_to_db_once
    loop lport in logical_port_list
        alt post_port_sfp_info_to_db != SFP_EEPROM_NOT_READY
             Note over SfpStateUpdateTask: post_port_dom_threshold_info_to_db
            opt PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS != MEDIA_SETTINGS_DONE
              opt if lport supports media settings
                  SfpStateUpdateTask ->> APPL_DB: PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = MEDIA_SETTINGS_NOTIFIED
                  APPL_DB -->> OA: Notify media settings for ports
                  Note over OA: Disable admin status<br>setPortSerdesAttribute
                  OA ->> APPL_DB: PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = MEDIA_SETTINGS_DONE
                  Note over OA: initHostTxReadyState
                end
            end
        else
            Note over SfpStateUpdateTask: retry_eeprom_set.add(lport)
        end
    end
    Note over SfpStateUpdateTask: _init_port_sfp_status_tbl<br>Subscribe to CONFIG_DB
    loop Wait for stop_event
        SfpStateUpdateTask ->> SfpStateUpdateTask: Handle config change event<br>retry_eeprom_reading()<br>_wrapper_get_transceiver_change_event
    end
```

## CMIS State machine with CMIS_STATE_MEDIA_SETTINGS_WAIT state

The below state machine is a high level flow and doesn't capture details for states other than CMIS_STATE_MEDIA_SETTINGS_WAIT

```mermaid
stateDiagram
    [*] --> CMIS_STATE_INSERTED
    state if_state <<choice>>
    state if_state2 <<choice>>
    CMIS_STATE_INSERTED --> if_state
    if_state --> CMIS_STATE_READY : if host_tx_ready != True or<br>admin_status != up<br> Action - disable TX
    if_state --> if_state2 : if host_tx_ready == True and<br>admin_status == up
    if_state2 --> CMIS_STATE_DP_DEINIT : if PORT_TABLE.port.CMIS_REINIT_REQUIRED == true or<br>is_cmis_application_update_required
    if_state2 --> CMIS_STATE_MEDIA_SETTINGS_WAIT : if is_media_settings_supported and<br>MEDIA_SETTINGS_SYNC_STATUS != MEDIA_SETTINGS_DONE
    note left of CMIS_STATE_READY : PORT_TABLE.port.CMIS_REINIT_REQUIRED = false
    if_state2 --> CMIS_STATE_FAILED : if appl < 1 or <br>host_lanes_mask <= 0 or <br>media_lanes_mask <= 0
    note left of CMIS_STATE_FAILED : PORT_TABLE.port.CMIS_REINIT_REQUIRED = false

    CMIS_STATE_MEDIA_SETTINGS_WAIT --> CMIS_STATE_DP_DEINIT : if PORT_TABLE&ltport&gt.MEDIA_SETTINGS_SYNC_STATUS == MEDIA_SETTINGS_DONE
    CMIS_STATE_MEDIA_SETTINGS_WAIT --> CMIS_STATE_INSERTED : Through force_cmis_reinit upon reaching timeout
    note right of CMIS_STATE_MEDIA_SETTINGS_WAIT
        Checks if PORT_TABLE&ltport&gt.MEDIA_SETTINGS_SYNC_STATUS == MEDIA_SETTINGS_DONE
        After 5s timeout, force_cmis_reinit will be called
    end note

    CMIS_STATE_DP_DEINIT --> CMIS_STATE_AP_CONF
    CMIS_STATE_AP_CONF --> CMIS_STATE_DP_INIT
    CMIS_STATE_DP_INIT --> CMIS_STATE_DP_TXON
    CMIS_STATE_DP_TXON --> CMIS_STATE_DP_ACTIVATE
    CMIS_STATE_DP_ACTIVATE --> CMIS_STATE_READY
```

## Transceiver OIR handling

```mermaid
sequenceDiagram
    participant STATE_DB
    participant OA
    participant APPL_DB
    participant CmisManagerTask
    participant SfpStateUpdateTask

    SfpStateUpdateTask ->> SfpStateUpdateTask : event = SFP_STATUS_REMOVED
    SfpStateUpdateTask -x STATE_DB : Delete TRANSCEIVER_INFO table for the port
    par         CmisManagerTask, SfpStateUpdateTask
        CmisManagerTask ->> CmisManagerTask : Transition CMIS SM to CMIS_STATE_REMOVED
        SfpStateUpdateTask ->> APPL_DB : PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = <br> MEDIA_SETTINGS_DEFAULT
    end

    SfpStateUpdateTask ->> SfpStateUpdateTask : event = SFP_STATUS_INSERTED
    SfpStateUpdateTask ->> STATE_DB : Create TRANSCEIVER_INFO table for the port
    par CmisManagerTask, SfpStateUpdateTask
        CmisManagerTask ->> CmisManagerTask : Transition CMIS SM to CMIS_STATE_INSERTED
        SfpStateUpdateTask ->> APPL_DB: PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = <br> MEDIA_SETTINGS_NOTIFIED
        activate OA
        APPL_DB -->> OA: Notify media settings for ports
        Note over OA: Disable admin status<br>setPortSerdesAttribute
        OA ->> APPL_DB: PORT_TABLE:<lport>.MEDIA_SETTINGS_SYNC_STATUS = MEDIA_SETTINGS_DONE
        Note over OA: initHostTxReadyState
        deactivate OA
    end
```

## XCVRD termination during syncd/swss/orchagent crash

The below sequence diagram captures the termination of XCVRD during syncd/swss/orchagent crash.
<br> supervisord will respawn XCVRD after termination as xcvrd is killed using SIGABRT signal

```mermaid
sequenceDiagram
    participant OA
    participant APPL_DB
    participant XCVRDMT as XCVRD main thread
    participant CmisManagerTask
    participant DomInfoUpdateTask
    participant SfpStateUpdateTask

    activate OA
    activate XCVRDMT
    activate CmisManagerTask
    activate DomInfoUpdateTask
    activate SfpStateUpdateTask
    OA -x OA: Crashes while handling a routine
    deactivate OA
    OA ->> APPL_DB : DEL PORT_TABLE

    XCVRDMT -x APPL_DB : XCVRD main thread proecesses DEL event of APPL_DB PORT_TABLE
    Note over XCVRDMT: generate_sigabrt = True
    alt If threads > 0 are dead
        XCVRDMT -x XCVRDMT : Kill XCVRD with SIGKILL
    end
    XCVRDMT -x CmisManagerTask : Stop CmisManagerTask
    deactivate CmisManagerTask
    XCVRDMT -x DomInfoUpdateTask : Stop DomInfoUpdateTask
    deactivate DomInfoUpdateTask
    XCVRDMT -x SfpStateUpdateTask : Stop SfpStateUpdateTask
    deactivate SfpStateUpdateTask
    Note over XCVRDMT : deinit()
    alt self.sfp_error_event.is_set()
        XCVRDMT -x XCVRDMT : sys.exit(SFP_SYSTEM_ERROR)
    else if generate_sigabrt is True
        XCVRDMT -x XCVRDMT : Kill XCVRD with SIGABRT

    else
        XCVRDMT -x XCVRDMT : Graceful exit
    end
    deactivate XCVRDMT
```

## Test plan and expectation
|       Event      | APPL_DB cleared | Xcvrd restarted | Media renotify | MEDIA_SETTINGS_SYNC_STATUS value on   xcvrd boot-up for initialized transceiver | CMIS re-init triggered | Link flap |
|:----------------:|:---------------:|:---------------:|:--------------:|:-----------------------------------------------------------------------------:|:----------------------:|:---------:|
| Xcvrd restart    | N               | Y               | N              | MEDIA_SETTINGS_DONE                                                           | N                      | N         |
| Pmon restart     | N               | Y               | N              | MEDIA_SETTINGS_DONE                                                           | N                      | N         |
| Swss restart     | Y               | Y               | Y              | MEDIA_SETTINGS_DEFAULT                                                        | Y                      | Y         |
| Syncd restart    | Y               | Y               | Y              | MEDIA_SETTINGS_DEFAULT                                                        | Y                      | Y         |
| config   reload  | Y               | Y               | Y              | MEDIA_SETTINGS_DEFAULT                                                        | Y                      | Y         |
| Cold reboot      | Y               | Y               | Y              | MEDIA_SETTINGS_DEFAULT                                                        | Y                      | Y         |
| Config shut      | N               | N               | N              | MEDIA_SETTINGS_DONE                                                           | N                      | Y         |
| Config no   shut | N               | N               | N              | MEDIA_SETTINGS_DONE                                                           | N                      | Y         |
| Warm   reboot    | N               | Y               | N              | MEDIA_SETTINGS_DONE                                                           | N                      | N         |
# Out of Scope 
Following items are not in the scope of this document. They would be taken up separately
1. CMIS API feature is not part of this design and the APIs will be used in this design. For CMIS HLD, Please refer to:
   https://github.com/sonic-net/SONiC/blob/9d480087243fd1158e785e3c2f4d35b73c6d1317/doc/sfp-cmis/cmis-init.md
2. Error handling of SAI attributes
   a) At present, If there is a set attribute failure, orch agent will exit. 
      Refer the error handling API : https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orch.cpp#L885
   b) Error handling for SET_ADMIN_STATUS attribute will be added in future.
   c) A propabale way to handle the failure is to set a error handling attribute to respective container syncd/GBsyncd with attribute that is failed. 
      The platform layer knows the error better and it will try to recover.

