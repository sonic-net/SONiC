# SONiC Platform Thermal enhancements #

# Table of Contents

* [SONiC Platform Thermal enhancements](#sonic-platform-thermal-enhancements)
* [Table of Contents](#table-of-contents)
      * [Revision](#revision)
* [About this Manual](#about-this-manual)
* [Scope](#scope)
   * [1. Thermalctld architecture and improvements](#1-thermalctld-architecture-and-improvements)
   * [2. Enhancements in Module chassis](#2-enhancements-in-module-chassis)
   * [2.1 Modular Chassis Thermalctld architecture](#21-modular-chassis-thermalctld-architecture)
   * [2.2. Transceiver thermal data in Linecard](#22-transceiver-thermal-data-in-linecard)
   * [2.3 Approaches to send transceiver thermal data from Linecard to Supervisor](#23-approaches-to-send-transceiver-thermal-data-from-linecard-to-supervisor)
      * [2.3.1 Send raw optics thermal data from Linecard to Supervisor](#231-send-raw-optics-thermal-data-from-linecard-to-supervisor)
            * [CHASSIS_STATE_DB Schema for Temperature_Info](#chassis_state_db-schema-for-temperature_info)
         * [2.3.1.1 Changes in thermalctld](#2311-changes-in-thermalctld)
            * [In LineCard](#in-linecard)
            * [In Supervisor](#in-supervisor)
      * [2.3.2 Process optics thermal data in Linecard send result to Supervisor](#232-process-optics-thermal-data-in-linecard-send-result-to-supervisor)
            * [CHASSIS_STATE_DB Schema for Thermal Algorithm result](#chassis_state_db-schema-for-thermal-algorithm-result)
         * [2.3.2.1 Changes in thermalctld](#2321-changes-in-thermalctld)
            * [In LineCard](#in-linecard-1)
            * [In Supervisor](#in-supervisor-1)
   * [3. Tests](#3-tests)
   * [4. Phases](#4-phases)
      
### Revision ###

 | Rev |     Date    |       Author                                                            | Change Description                |
 |:---:|:-----------:|:-----------------------------------------------------------------------:|-----------------------------------|
 | 0.1 | 10/08/2025  |  Judy Joseph                                                            | Initial version                   |
 | 0.5 | 04/06/2026  |  Judy Joseph                                                            | Updated this as a common design   |

 
# About this Manual
This document provides design improvements in thermalctld daemon in pmon for pizzabox and chassis devices

# Scope
This document covers all variants of sonic platforms

#Requirements
1. Unified thermal control workflow across all sonic platforms 
  * Thermalctld not to get the thermal data for optical transceivers. 
  * It gets thermal data for all other sensors and stores in Redis DB. 
  * If sensors like CPU/ASIC etc. needs to be read faster, we can introduce the infra to have a separate timer.
2. Better debuggability – we can stream out data from DB to telemetry server for triage/analysis.
3. The thermal algorithm to be invoked from thermalctld.ThermalControlDaemon process via the call self.thermal_manager.run_policy(self.chassis)
4. Scalable, clearly define boundaries for thermalctld and xcvrd, will not see issues like i2c lockup on devices with many interfaces.
5. Common thermal algorithm for all sonic platforms, instead of proprietary cooling algorithms which each vendor must maintain.


## 1. Thermalctld architecture and improvements

## 2. Enhancements in Module chassis

## 2.1 Modular Chassis Thermalctld architecture

In the Modular chassis, thermalctld daemon runs in pmon docker on the Linecard and Supervisor card. It has ThermalControlDaemon thread which runs the thermal policy algorithm, and does policy actions to keep chassis cool by running fan at optimal speed. 

It also spawns ThermalMonitor thread which uses the TemperatureUpdater class to get the thermals available in the device either Linecard or Supervisor and updates then in the local STATE_DB. In addition the thermalctld/ThermalMonitor in Linecard push this data to CHASSIS_STATE_DB in Supervisor card. 

Today only the non-optics thermal data is pushed from Linecard to Supervisor via redis CHASSIS_STATE_DB approach. 

The thermal sensor points is defined under the section "thermals" in the platform.json for that platform/sku.
   
## 2.2. Transceiver thermal data in Linecard
The optics temperature infromation is retrieved by the dom_mgr thread in the xcvrd daemon in the respective Linecards and stored in the TRANSCEIVER_DOM_SENSOR|Ethernet<> table in STATE_DB. The thresholds are stored in TRANSCEIVER_DOM_THRESHOLD|Ethernet<> table in STATE_DB. 

This table is present in the STATE_DB of host database in case of single ASIC devices and in the STATE_DB of respective namespace database in case of multi-asic platforms.

```
"TRANSCEIVER_DOM_SENSOR|Ethernet<>"
  temperature <value>
```
```
"TRANSCEIVER_DOM_THRESHOLD|Ethernet8"
  temphighalarm     <value>
  templowalarm      <value>
  temphighwarning   <value>
  templowwarning    <value>
```
This data is already streamed out of the Linecard from these tables, so that external tools can monitor the optics temperature.

## 2.3 Approaches to send transceiver thermal data from Linecard to Supervisor
  There are two approaches to send the transceiver thermal data from Linecard to Supervisor as detailed below

### 2.3.1 Send raw optics thermal data from Linecard to Supervisor

 This case where thermalctld in each Linecard/module **don't** process thermal data locally, instead just send each optics Temperature_info(along with the other thermals) to Supervisor CHASSIS_STATE_DB. 
 
 Following schema could be used to store the TEMPERATURE_INFO in the CHASSIS_STATE_DB, it follows the same schema as other thermals. Here the Sensor-Name will be the respective interface name.
 
 ##### CHASSIS_STATE_DB Schema for Temperature_Info
 ```
 key                                   = TEMPERATURE_INFO_<card-index>|<Sensor-Name>; 
 ; field                               = value
 temperature_high_alarm                = float;
 temperature_low_alarm                 = float;   
 temperature_high_warning              = float;
 temperature_low_warning               = float;
 temperature                           = float;
 ```

#### 2.3.1.1 Changes in thermalctld

##### In LineCard

The thermalctld/TemperatureUpdater class implementaion in the ThermalMonitor thread should get the optics temerature from the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table per interface.
* It is already connected to the STATE_DB in database service running in the host namespace.
* For multi-asic platforms, there will be additional change to connect to the STATE_DB in database service running in the namespaces where TRANSCEIVER_DOM tables are present.
* Additional change to push this data to CHASSIS_STATE_DB as it is done for other thermal sensors.

##### In Supervisor

The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. 

This run_policy/_collect_thermal_information() implementaion for vendor/platform should gather all the thermals which includes Supervisor thermals sensors + optics and no-optics thermals pushed from various Linecards in CHASSIS_STATE_DB, invoke the platform/vendor specific cooling algorithm to derive the cooling parameters for the chassis.

 ```
 TEMPERATURE_INFO_1|*thermals/optics*
 TEMPERATURE_INFO_2|*thermals/optics*
 TEMPERATURE_INFO_3|*thermals/optics*
 ...
 TEMPERATURE_INFO_SUP|*thermals*
```
  
### 2.3.2 Process optics thermal data in Linecard send result to Supervisor

 This case where thermalctld in each Linecard/module processes thermal data including that of thermal sensors and interfaces/optics locally on the linecard itself using vendor/platform API and sends the thermal algorithm result to Supervisor CHASSIS_STATE_DB. 
 
 The Database schema used will be a union of attributes which platform/vendor thermal algorithm calculates, which can be defined in the platform.json file ( as shown below). 
 It could be attributes like recommended fan speed, pwm value, temperature of the hotest sensor/optic etc.
 
 platform.json to have a new key named "linecard_thermal_algorithm_result" to define platform specific thermal algorithm result
 ```
         "linecard_thermal_algorithm_result": {
            "vendor_attribute_name": "board_sensor",
            "vendor_attribute_value": 1.0,
            "vendor_attribute_threshold": 5.0
        }
 ```

##### CHASSIS_STATE_DB Schema for Thermal Algorithm result
 ```
 key                                   = TEMPERATURE_INFO_<card-index>|THERMAL_ALGO_RESULT; 
 ; field                               = value
 vendor_attribute_name                = string;
 vendor_attribute_value               = float;
 vendor_attribute_threshold           = float;
 ```
  
#### 2.3.2.1 Changes in thermalctld

##### In LineCard

The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. 

This run_policy() implementaion should gather all local thermals including optics from the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table ( from the respective namespaces for multi-asic platforms ) and compute the thermal algorithm result attributes
* Introduce a new API inThermalManagerBase class to fetch the thermal algorithm result attributes, in case of Linecard in a chassis. This needs to be implemented by vendor/platform API.
* The thermalctld/ThermalControlDaemon fetch/store the thermal algorithm result in local STATE_DB in the Linecard  as "TEMPERATURE_INFO|THERMAL_ALGO_RESULT"
* The thermalctld/TemperatureUpdater in the ThermalMonitor thread would push the above thermal algorithm result to CHASSIS_STATE_DB in supervisor with the DB schema defined for Thermal Algorithm Result above.

##### In Supervisor

The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. 

This run_policy/_collect_thermal_information() implementaion for vendor/platform should gather all the thermals including the Supervisor thermals sensors and the thermal_algo_result which was pushed from various Linecards in CHASSIS_STATE_DB in Supervisor, invoke the platform/vendor specific cooling algorithm to control the fan/cooling in chassis.

 ```
 TEMPERATURE_INFO_1|*THERMAL_ALGO_RESULT*
 TEMPERATURE_INFO_2|*THERMAL_ALGO_RESULT*
 TEMPERATURE_INFO_3|*THERMAL_ALGO_RESULT*
 ...
 TEMPERATURE_INFO_SUP|*thermals*
```

**Note:** The imers currently used in thermalctld "INTERVAL" and "UPDATE_INTERVAL" needs to be fine tuned per platform. 
          We can add knobs for thermalctld daemon in "pmon_daemon_control.json" to add timer values.
          


## 3. Tests

## 4. Phases

