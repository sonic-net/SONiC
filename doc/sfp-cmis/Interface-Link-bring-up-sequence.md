# Feature Name
Deterministic Approach for Interface Link bring-up sequence

# High Level Design Document
#### Rev 0.2

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About This Manual](#about-this-manual)
  * [Abbreviation](#abbreviation)
  * [References](#references)
  * [Problem Definition](#problem-definition)
  * [Background](#background)
  * [Objective](#objective)
  * [Proposal](#proposal)
  * [Proposed Work-Flows](#proposed-work-flows)

# List of Tables
  * [Table 1: Definitions](#table-1-definitions)
  * [Table 2: References](#table-2-references)

# Revision
| Rev |     Date    |       Author                       | Change Description           |
|:---:|:-----------:|:----------------------------------:|------------------------------|
| 0.1 | 08/16/2021  | Shyam Kumar                        | Initial version                       
| 0.2 | 12/13/2021  | Shyam Kumar,  Jaganathan Anbalagan | Added uses-cases, workflows  |


# About this Manual
Its a high-level design document describing the need to have determinstic approach for
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
| CMIS v5 | [CMIS5p0.pdf](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf) |


# Problem Definition

1.	Presently in SONiC, there is no synchronization between 400G Datapath Init operation and enabling ASIC (NPU/PHY) Tx which may cause link instability during administrative interface enable “config interface startup Ethernet” configuration and bootup scenarios. 
      
    For 400G optics module, the Host (NPU/PHY) needs to provide a valid high-speed Tx input signal at the required signaling rate and encoding type prior to causing a DPSM to exit from DPDeactivated state and to move to DP Init transient state.
      
    Fundamentally it means - have a deterministic approach to bring-up the interface.
      
    Also, this problem is mentioned ‘as outside-the-scope’ of ‘CMIS Application Initialization’ high-level design document
      **(https://github.com/ds952811/SONiC/blob/0e4516d7bf707a36127438c7f2fa9cc2b504298e/doc/sfp-cmis/cmis-init.md#outside-the-scope)**

2.  During administrative interface disable “config interface shutdown Ethernet”, only the ASIC(NPU) Tx is disabled and not the optics laser for 100G/400G. 
      This will lead to power wastage and un-necessary fan power consumption to keep the module temperature in operating range 

# Background

  Per the ‘QSFPDD spec’,  ‘validation, diagnostics’ done by HW team' and 'agreement with vendors', 
  need to follow following bring-up seq to enable port/interface with 400G optics in LC/chassis:

    a) Enable port on NPU (bring-up port, serdes on the NPU ; enable signals) : syncd
    b) Enable port on PHY (bring-up port, serdes on the PHY ; enable signals) : gbsyncd
       - Wait for signal to stabilize on PHY   
    c) Enable optical module (turn laser on/ enable tx) : xcvrd or platform bootstrap/infra

  In boards not having PHY, #b) not needed but #a) and #c) sequence to be followed.
  
  ## Clause from QSFP-DD (CMIS4.0 spec)
  
     Excerpt from CMIS4.0 spec providing detailed reasoning for the above-mentioned bring-up sequence
     
  ![61f5b485-cf3b-4ca8-beac-9102b6feabfe](https://user-images.githubusercontent.com/69485234/147173702-f124fc9d-ef27-4816-b1a1-b4a44a5833a7.PNG)


  ## Clause from QSFP-DD (CMIS5.0 spec)
  
     Excerpt from CMIS5.0 spec providing detailed reasoning for the above-mentioned bring-up sequence
     
  ![96a35dc5-618f-418c-9593-5639a90f1b28](https://user-images.githubusercontent.com/69485234/147173164-5ad0123c-479a-4774-b3ee-12a81fdd7d7e.PNG)
     

# Objective

Have a determistic approach for Interface link bring-up sequence i.e. below sequence to be followed:
  1. Initialize and enable NPU Tx and Rx path
  2. For system with 'External' PHY: Initialize and enable PHY Tx and Rx on both line and host sides; ensure host side link is up 
  3. Then only perform optics data path initialization/activation/Tx enable (for 400G) and Tx enable (for 100G) 

# Proposal

Recommend following this high-level work-flow sequence to accomplish the Objective:
- xcvrd to subscribe to a new field “host_tx_ready” in port table state-DB
- Orchagent will set the “host_tx_ready” to true/false based on the SET_ADMIN_STATE attribute return status to syncd/gbsyncd. (As part of SET_ADMIN_STATE attribute enable, the NPU Tx is enabled)
- xcvrd process the “host_tx_ready” value change event and do optics datapath init / de-init using CMIS API
- Recommendation is to follow this proposal for all the known interfaces - 400G/100G/40G/25G/10G. Reason being: 
  - 400G - as mentioned above the CMIS spec to be followed
  - 100G/40G/25G/10G - 
    - deterministic approach to bring the interface will eliminate any link stability issue which will be difficult to chase in the production network
    - there is a possibility of interface link flaps with non-quiescent optical modules <QSFP+/SFP28/SFP+> if this 'deterministic approach' is not followed
    - It helps bring down the optical module laser when interface is adminstiratively shutdown. Per the workflow here, this is acheived by xcvrd listening to host_tx_ready field from PORT_TABLE of STATE_DB. Turning the laser off would reduce the power consumption and avoid any lab hazard
    - Additionally provides uniform workflow across all interface types instead of just 400G
  - This synchronization will also benefit native 10G SFPs interfaces as they are "plug N play" and may not have quiescent functionality. (xcvrd can use the optional 'soft tx disable' ctrl reg to disable the tx)

# Proposed Work-Flows
Please refer to the  flow/sequence diagrams which covers the following required use-cases
  - Transceiver initialization
  - admin enable configurations 
  - admin disable configurations

# Transceiver Initialization 
  (at platform bootstrap layer)
  
  ![LC boot-up sequence - optics INIT (platform bootstrap)](https://user-images.githubusercontent.com/69485234/147166795-5665670d-dd2b-4b6f-976c-eabcc65d5448.png)

# Applying 'interface admin startup' configuration

![LC boot-up sequence - 'admin enable' Config gets applied](https://user-images.githubusercontent.com/69485234/147166867-56f3e82d-1b1c-4b7a-a867-5470ee6050e7.png)


# Applying 'interface admin shutdown' configuration

![LC boot-up sequence - 'admin disable' Config gets applied](https://user-images.githubusercontent.com/69485234/147166884-92c9af48-2d64-4e67-8933-f80531d821b4.png)




