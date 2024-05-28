# PMON Enhancement -- Shutdown/Startup SFM module
# High Level Design Document
### Rev 1.0
- [About this Manual](#about-this-manual)
- [Scope](#scope)
- [Background](#background)
- [1 Requirements Overview](#1-requirements-overview)
  * [1.1 Functional Requirements](#11-functional-requirements)
- [2 Design Details](#2-design-details)
  * [2.1 Using the existing CLI command "sudo config chassis module shutdown/startup <module_name>" by modifying/enhancing the chassis_module.py](#21-using-the-existing-cli-command--sudo-config-chassis-module-shutdown-startup--module-name---by-modifying-enhancing-the-chassis-modulepy)
  * [2.2 Modify the vendor specified set_admin_state() in the module.py](#22-modify-the-vendor-specified-set-admin-state---in-the-modulepy)
  * [2.3 Modify the ModuleUpdater in chassisd.](#23-modify-the-moduleupdater-in-chassisd)
- [3 Impact and Test Considerations](#3-impact-and-test-considerations)
  * [3.1 Impact of the PCIed and Thermal sensors](#31-impact-of-the-pcied-and-thermal-sensors)
  * [3.2 Test](#32-test)
- [4 References](#4-references)

<small><i><a href='http://ecotrust-canada.github.io/markdown-toc/'>Table of contents generated with markdown-toc</a></i></small>

###### Revision
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 05/03/2024  | Marty Lok                                                                   | Initial public version            |

# About this Manual
This document describes the requirements for reset System Fabric Module (SFM)  on a Chassis and the planned design/code changes for supporting this enhancement.

# Scope
This scope of this specification is using the existing module shutdown/startup commands and the modification supports resetting of the SFM Module

# Background
In order to avoid the crash of the Swss/Syncd processes of a SFM module, when a SFM module in a chassis is required to be reseated or hot swapped, a proper shutdown and startup procedure needs to be followed.  


# 1 Requirements Overview
## 1.1 Functional Requirements
This section describes the requirement for using existing CLI command shutdown/startup a SFM module on a Chassis system.  
1. Using the existing CLI command "sudo config chassis module shutdown/startup <module_name>" to shutdown/startup a SFM module
2. Module remains down state if system is booting up with a configuration file which contains a module is set to down state

# 2 Design Details
The following changes are implementation and modification.
## 2.1 Using the existing CLI command "sudo config chassis module shutdown/startup <module_name>" by modifying/enhancing the chassis_module.py 
1. Define and create a new method fabric_module_set_admin_status() with the following actions
  * Derive a list of ASIC number (asic_list) which is assoicated with this module_name from the CHASSIS_FABRIC_ASIC_TABLE in the CHASSIS_STATE_DB
  * For shutdown case:
    - Loop this asic_list and call the "systemctl stop" to stop the related swss@ and syncd@ services.
    - Delete the related CHASSIS_FABRIC_ASIC_TABLE entries in the CHASSIS_STATE_DB
    - Loop this asic_list and call the "systemctl start" to start the related swss@ and syncd@ service.  The association of service ASIC number with a SFM module is platform specified. If we don't restart of the service here, we are not able to derive the asic_list which is assoicted with this Module when user issues CLI command to start up this SFM module since CHASSIS_FABRIC_ASIC_TABLE entry has been deleted. 
    
  * For startup case:
    - Loop the asic_list and call the "systemctl start" to start the related swss@ and syncd@ service
2. Modify the existing shutdown_chassis_module() and startup_chassis_module() method to all the fabric_module_set_admin_status()
  * In order to avoid the raised condition of the chassisd re-populates CHASSIS_FABRIC_ASIC_TABLE entry while the shutdown command is executing, the implementation needs to make sure the new admin_status has been set to Redis DB before proceeds to stop related swss/syncd service and remove the CHASSIS_FABRIC_ASIC_TABLE  entry. The get_config_module_state_timeout() function is introduced to verify the config value setting in Redis DB.

## 2.2 Modify the vendor specified set_admin_state() in the module.py
Modify the set_admin_state() in module.py for SFM module to shutdown/startup a SFM module. This function is already called by the existing ConfigManagerTask class which subscribes the CHASSIS_MODULE in the CONFIG_DB to shutdown/startup a module when user issues the CLI command "sudo config chassis module shutdown/startup <module_name>" on the Supervisor. 

## 2.3 Modify the ModuleUpdater in chassisd.
Modify the ModuleUpdater class in chassisd to keep a SFM module in the down state when system is booting up with a configuration which contains a shutdown of a SMF module.
1. Create and add a new function get_module_admin_status() to get the admin_status from CHASSIS_CONFIG_TABLE in CONFIG_DB
2. Modify the module_db_update() to call get_module_admin_status() to check the config module. If the module_cfg_status is not set to down, then populate the CH-TBDASSIS_FABRIC_ASIC_TABLE. Otherwise, just ignore it even the SFM module is present. This mechanism prevents the event is triggered in the swss.sh when admin_status is set to down state.


# 3 Impact and Test Considerations
## 3.1 Impact of the PCIed and Thermal sensors
For PCIed, based on the investigation, the current design of the Fabric module shutdown has NO impact on the PCIed.  The PCIed current checks the basic PCI components. For the Fabric slot which is shutdown, if platform supports PCI on the Fabric card, it should check if its power is on that particular card before it is added to the PCIe check. That is how is handled in the Arista vendor code.
For the thermal sensors of the Fabric card, this should be handled by the vendor's specified code. If module is shutdown, the vendor sonic-platform thermal query should not return any entry for that particular slot. 

## 3.2 Test
UTs are also added to simulate the Fabric shutdown and startup

# 4 References
-TBD


