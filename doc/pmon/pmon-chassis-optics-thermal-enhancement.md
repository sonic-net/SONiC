# SONiC Chassis Platform Optics Thermal Management & Monitoring #

### Rev 1.0 ###

# Table of Contents

* [About this Manual](#about-this-manual)
* [Scope](#scope)
  * [1. Modular Chassis Thermalctld architecture](#1-modular-chassis-thermalctld-architecture)
  * [2. Transceiver thermal data in Linecard](#2-transceiver-thermal-data-in-linecard)
    * [2.1 Retrieve optics temperature data in Linecard](#21-retrieve-optics-temperature-data-in-linecard)
  * [3. Approaches to send transceiver thermal data from Linecard to Supervisor](#3-approaches-to-send-transceiver-thermal-data-from-linecard-to-supervisor)
    * [3.1 Send raw optics thermal data from Linecard to Supervisor](#31-send-raw-optics-thermal-data-from-linecard-to-supervisor)
    * [3.2 Process optics thermal data in Linecard send result to Supervisor](#32-process-optics-thermal-data-in-linecard-send-result-to-supervisor)    
  * [4. Tests](#4-tests)

      
### Revision ###

 | Rev |     Date    |       Author                                                            | Change Description                |
 |:---:|:-----------:|:-----------------------------------------------------------------------:|-----------------------------------|
 | 1.0 | 10/08/2025  |  Judy Joseph                                                            | Initial version                   |
 
# About this Manual
This document provides design approaches to handling transceiver thermal data in Linecard, use it in cooling algorithm in Supervisor.

# Scope
This document covers both the packet chassis and voq chassis 

## 1. Modular Chassis Thermalctld architecture
In the Modular chassis the thermalctld daemon runs in pmon docker on the Linecard and Supervisor card. It has ThermalControlDaemon thread which runs the thermal policy algorithm and spawns ThermalMonitor thread. ThermalMonitor use the TemperatureUpdater class to get the thermals available in the device either Linecard or Supervisor and updates then in the local STATE_DB + push the data to CHASSIS_STATE_DB in Supervisor card. 

The thermal sensor points is defined under the section "thermals" in the platform.json for that platform/sku.
   
## 2. Transceiver thermal data in Linecard
The optics temperature infromation is retrieved by the dom_mgr thread in the xcvrd daemon in the respective Linecards and stored in the TRANSCEIVER_DOM_SENSOR|Ethernet<> table in STATE_DB. The temperature thresholds are stored in TRANSCEIVER_DOM_THRESHOLD|Ethernet<> table in STATE_DB.

### 2.1 Retrieve optics temperature data in Linecard

The data is already stored locally in the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table per interface. This table is present in the STATE_DB of host database in case of single ASIC devices and in the STATE_DB of respective namespace database in case of multi-asic platforms.
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
This data is already streamed out of the Linecard, so that external tools can monitor the optics temperature.

## 3. Approaches to send transceiver thermal data from Linecard to Supervisor
  There are two approaches to send the transceiver thermal data from Linecard to Supervisor as detailed below

### 3.1 Send raw optics thermal data from Linecard to Supervisor

 This case where thermalctld in each Linecard/module **don't** process thermal data locally, instead just send each optics Temperature_info(along with the other thermals) to Supervisor CHASSIS_STATE_DB. Following schema could be used to store the TEMPERATURE_INFO in the CHASSIS_STATE_DB, it follows the same schema as other thermals. Here the Sensor-Name will be the respective interface name.
 
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

#### 3.1.1 Changes in thermalctld

##### In LineCard

The thermalctld/TemperatureUpdater class implementaion in the ThermalMonitor thread should get the optics temerature from the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table per interface.
* It is already connected to the STATE_DB in database service running in the host namespace.
* For multi-asic platforms, there will be additional change to connect to the STATE_DB in database service running in the namespaces where TRANSCEIVER_DOM tables are present.
* Push it to CHASSIS_STATE_DB as it is done for other thermal sensors.

##### In Supervisor

The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. This run_policy() implementaion should gather all the thermals which includes Supervisor thermals sensors + optics and no-optics thermals pushed from various Linecards in CHASSIS_STATE_DB, invoke the platform/vendor specific cooling algorithm to derive the cooling parameters for the chassis.
 ```
 TEMPERATURE_INFO_1|*thermals/optics*
 TEMPERATURE_INFO_2|*thermals/optics*
 TEMPERATURE_INFO_3|*thermals/optics*
 ...
 TEMPERATURE_INFO_SUP|*thermals*
```
  
### 3.2 Process optics thermal data in Linecard send result to Supervisor

 This case where thermalctld in each Linecard/module processes thermal data including that of thermal sensors and interfaces/optics locally on the linecard itself using vendor/platform API and sends the thermal algorithm result to Supervisor CHASSIS_STATE_DB. The schema used will be a union of all the attributes which platform/vendor algorithm outputs, which can be defined in the platform.json file ( as shown below). It could be attributes like recommended fan speed, pwm value, temperature of the hotest sensor/optic etc.
 
 ##### platform.json to have a new key named "linecard_thermal_algorithm_result" to define platform specific thermal algorithm result
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
  
#### 3.2.1 Changes in thermalctld

##### In LineCard

The thermalctld/TemperatureUpdater class implementaion in the ThermalMonitor thread should get the optics temerature from the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table per interface.
* The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. This run_policy() implementaion should gather all the thermals which includes local thermal sensors and optics temerature from the TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD table ( in the respective namespaces for multi-asic platforms ), and it derives the thermal algorithm result attributes
* The thermal algorithm result attributes is stored locally in the Linecard  as "TEMPERATURE_INFO|THERMAL_ALGO_RESULT" in the STATE_DB
* The thermalctld/TemperatureUpdater in the ThermalMonitor thread would push the above thermal algorithm result to CHASSIS_STATE_DB as it is done for other thermal sensors.

##### In Supervisor

The thermalctld/ThermalControlDaemon thread calls the thermal_manager.run_policy(self.chassis) routine. This run_policy() implementaion should gather all the thermals including the Supervisor thermals sensors and the thermal_algo_result which was pushed from various Linecards in CHASSIS_STATE_DB in Supervisor, invoke the platform/vendor specific cooling algorithm to control the fan/cooling in chassis.
 ```
 TEMPERATURE_INFO_1|*thermal_algo_result*
 TEMPERATURE_INFO_2|*thermal_algo_result*
 TEMPERATURE_INFO_3|*thermal_algo_result*
 ...
 TEMPERATURE_INFO_SUP|*thermals*
```

## 4. Tests

