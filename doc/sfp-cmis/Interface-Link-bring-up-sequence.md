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


# Out of Scope 
Following items are not in the scope of this document. They would be taken up separately
1. xcvrd restart 
   - If the xcvrd goes for restart, then all the DB events will be replayed. 
     Here the Datapath init/activate for CMIS compliant optical modules, tx-disable register set (for SFF complaint optical modules), will be a no-op if the optics is already in that state 
2. syncd/gbsyncd/swss docker container restart
   - Cleanup scenario - Check if the host_tx_ready field in STATE-DB need to be updated to “False” for any use-case, either in going down or coming up path 
   - Discuss further on the possible use-cases
3. CMIS API feature is not part of this design and the APIs will be used in this design. For CMIS HLD, Please refer to:
   https://github.com/sonic-net/SONiC/blob/9d480087243fd1158e785e3c2f4d35b73c6d1317/doc/sfp-cmis/cmis-init.md
4. Error handling of SAI attributes
   a) At present, If there is a set attribute failure, orch agent will exit. 
      Refer the error handling API : https://github.com/sonic-net/sonic-swss/blob/master/orchagent/orch.cpp#L885
   b) Error handling for SET_ADMIN_STATUS attribute will be added in future.
   c) A propabale way to handle the failure is to set a error handling attribute to respective container syncd/GBsyncd with attribute that is failed. 
      The platform layer knows the error better and it will try to recover.

