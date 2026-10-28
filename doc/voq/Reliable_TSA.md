# Reliable TSA
# High Level Design Document
### Rev 1.2

# Table of Contents
  * [Revision](#revision)

  * [About this Manual](#about-this-manual)

  * [Scope](#scope)

  * [Background](#background)

  * [1 Requirements Overview](#1-requirements-overview)
    * [1.1 Functional requirements](#11-functional-requirements)
  * [2 Design Details](#2-design-details)
    * [2.1 CHASSIS-APP-DB](#21-chassis-app-db)
  * [3 Test Considerations](#5-test-considerations)
  * [4 References](#7-references)

###### Revision
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 04/18/2024  | Srikanth Keesara                                                                   | Initial public version            |

# About this Manual
This document describes the requirements for Reliable TSA on a VOQ Chassis and the planned design/code changes for supporting this enhancement.

# Scope
This scope of this specification is the TSA/TSB commands and the implementation supporting those commands on a VOQ Chassis.

# Background
The TSA feature can be used to shift traffic away from a Sonic Router. This is achieved by applying a Route Policy to BGP which causes it to not advertize any Routes to its Neighbors. This capability is useful when commissioning a new Device  or prior to beginning maintenance operations on a device that may already in production. In a Chassis based system that is made up of multiple Line Cards and a Supervisor Card each running a separate instance of the Sonic software - the TSA feature currently works as follows.
    1. The TSA/TSB commands on the Line Card updates the CONFIG_DB on the Line Card. This update is picked up and processed by the bgpcfgd process.
    2. The TSA/TSB commands on the Supervisor causes the Supervisor to SSH to each Line Card in sequence and issue the same command on the Line Card.

This implementation of the commands on the Supervisor is not adequate for a Chassis System. Some issues -
   1. There could be a decent amount of delay when the First Line Card acts on the command to when the last Line Card acts on it. A Unresponsive or a slow to respond Line Card can cause significant delays to the Line Cards behinnd it.
   2. An unresponsive Line Card will never receive and act on the command. This will be the case even if the Line is rebooted.
   3. Using the TSA/TSB commands have the effect of erasing the TSA/TSB configuration on the Line Cards. This makes it difficult to operate different Line Cards in a chassis with different TSA settings.


# 1 Requirements Overview
## 1.1 Functional Requirements
This sections describes the requirements for the TSA on the Supervisor and the Line Cards. These requirements only affect the VOQ Chassis systems. Specifically T0/T1 non Chassis system should not be impaced.
1. The TSA is an independent configuration attribute (tsa_enabled) on the Supervisor host CONFGI_DB and the per asic CONFIG_DB on the Line Card. 
2. TSA/TSB commands on the Supervisor should only change the Supervisor host config.
3. TSA/TSB commands on the Line Card should only change the config of the asics on that line card.
4. Changes to Supervisor config should also be reflected into the CHASSIS_APP_DB. The asic instances of all Line Cards subscribe to the tsa_enabled attribute of the CHASSIS_APP_DB.
5. The net operational TSA state of BGP on the asics of a LC is a function of the TSA configuration of the Supervisor and the LC
6. If Supervisor tsa_enabled == TRUE, operational state is TSA(TRUE). In this configuration -
   A. After the Line card reboots - the operational state will be TSA when the Line card comes back up. The "startup_tsa_tsb" service will still set the local CONFIG_DB attribute and start a timer. If the timer expires while Supervisor is still "tsa_enabled", the operational state will still be TSA.
   B. After "Config reload" - the operational state will be TSA.
   C. After any of the dockers get restarted (crash, service restart etc..) - the operational state will be TSA.
   D. The Line Card "startup_tsa_tsb" service will still kick-in after a LC reboot After a Line Card 
7. If Supervisor tsa_enabled == FALSE, operational TSA state is controlled by LC tsa_enabled config (including the startup_tsa_tsb service if the LC reboots)
8. If Supervisor config changes from tsa_enabled == TRUE to tsa_enabled == FALSE : Operational state should be changed only if LC tsa_enabled == FALSE
9. Should support saving Supervisor TSA configuration host config_db.json file (on the Supervisor)
10. Supervisor reboot or config reload should restore state from the host config_db.json file of the Supervisor.

# 2 Design Details
The following changes are planned.
1. Add a new tsa_enabled attribute to CHASSIS_APP_DB
2. Uppdate the "tsa_enabled" attribute in Supervisor (CONFIG_DB) when TSA/TSB commands are issued on Supervisor (also on bootup if Supervior config_db.json files has tsa_enabled set)
3. TSA/TSB command scripts are modified such that on the Supervisor card of a VOQ Chassis - they update the tsa_enabled attribute of CHASSIS_APP_DB
4. Modify bgpcfgd to subscribe to updates to the tsa_enabled attribute of CHASSIS_APP_DB
5. Modify bgpcfgd to take into account the values of tsa_enabled attributes of both the CHASSIS_APP_DB and the local CONFIG_DB when determining whether BGP should be in TSA or TSB state. This should be done in a manner that complies with the requirements set above.

## 2.1 CHASSIS-APP-DB
The following is added to CHASSIS-APP-DB for Supervisor TSA  
  "BGP_DEVICE_GLOBAL|STATE": {
    {
      "tsa_enabled": {"true" | "false"}
    }
  }

# 3 Test Considerations
TBD - Add unit test details
TBD - Add some description of sonic-mgmt tests that will be needed

# 4 References
To be completed
