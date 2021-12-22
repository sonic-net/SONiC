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
  * [Requirement](#requirement)  

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

# Requirement

## Problem Definition

  1.	Presently in SONiC, there is no synchronization between 400G Datapath Init operation and enabling ASIC (NPU/PHY) Tx which may cause link instability during administrative interface enable “config interface startup Ethernet” configuration and bootup scenarios. 
      For 400G optics module, The Host (NPU/PHY) needs to provide a valid high-speed Tx input signal at the required signaling rate and encoding type prior to causing a DPSM to exit from DPDeactivated state and to move to DP Init transient state.
      Fundamentally it means - have a deterministic approach to bring-up the interface.

      Also, this problem is mentioned ‘as outside-the-scope’ of ‘CMIS Application Initialization’ high-level design document
      https://github.com/ds952811/SONiC/blob/0e4516d7bf707a36127438c7f2fa9cc2b504298e/doc/sfp-cmis/cmis-init.md#outside-the-scope  

  2.  During administrative interface disable “config interface shutdown Ethernet”, only the ASIC(NPU) Tx is disabled and not the optics laser for 100G/400G. 
      This will lead to power wastage and un-necessary fan power consumption to keep the module temperature in operating range 


## Background/Context

  Per the ‘QSFPDD spec’,  ‘validation, diagnostics’ done by HW team' and 'agreement with vendors', 
  need to follow following bring-up seq to enable port/interface with 400G optics in LC/chassis:
  
    a) Enable port on NPU (bring-up port, serdes on the NPU ; enable signals) : syncd

    b) Enable port on PHY (bring-up port, serdes on the PHY ; enable signals) : gbsyncd
       - Wait for signal to stabilize on PHY   

    c) Enable optical module (turn laser on/ enable tx) : xcvrd or platform bootstrap/infra

  In boards not having PHY, 2nd point not needed but 1st & 3rd sequence to be followed.
  
  ### Clause from QSFP-DD (CMIS4 spec)
    
  ### Cluase from QSFP-DD (CMIS5 spec)

# Objective

The 400G optics data path initialization to be invoked only ‘after the NPU is initialized and Tx is enabled’ for the port. 
For the External PHY based board, also need to ensure that ‘PHY is initialized, and Tx is enabled on the PHY’.

# Proposal

- xcvrd to subscribe to a new field “host_tx_ready” in port table state-DB
- Orchagent will set the “host_tx_ready” to true/false based on the SET_ADMIN_STATE attribute return status to syncd/gbsyncd. (As part of SET_ADMIN_STATE attribute enable, the NPU Tx is enabled)
- xcvrd process the “host_tx_ready” value change event and do optics datapath init / de-init using CMIS API
- Recommendation is to follow this proposal for all the known interface speeds - 400G/100G/40G/25G/10G
  - 400G - as mentioned above the CMIS spec to be followed
  - 100G/40G/25G/10G - deterministic approach to bring the interface will eliminate any link stability issue which will be difficult to chase in the production network
  - This synchronization will also benefit native 10G SFPs interfaces as they are "plug N play" and may not have quiescent functionality. (xcvrd can use the optional 'soft tx disable' ctrl reg to disable the tx)

# Proposed Work-Flows
Please refer to the  flow/sequence diagrams which covers the following required use-cases
  - LC boot-up
  - optics initialization
  - admin enable, disable configurations 

# Optics Initialization 
  (at platform bootstrap layer)
  
  [LC boot-up sequence - optics INIT (platform bootstrap).pdf](https://github.com/Azure/SONiC/files/7765096/LC.boot-up.sequence.-.optics.INIT.platform.bootstrap.pdf)

# Applying 'interface admin startup' configuration

[LC boot-up sequence - 'admin enable' Config gets applied.pdf](https://github.com/Azure/SONiC/files/7765098/LC.boot-up.sequence.-.admin.enable.Config.gets.applied.pdf)

# Applying 'interface admin shutdown' configuration

[LC boot-up sequence - 'admin disable' Config gets applied.pdf](https://github.com/Azure/SONiC/files/7765100/LC.boot-up.sequence.-.admin.disable.Config.gets.applied.pdf)


