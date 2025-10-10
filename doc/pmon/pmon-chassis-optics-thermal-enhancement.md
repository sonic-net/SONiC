# SONiC Chassis Platform Optics Thermal Management & Monitoring #

### Rev 1.0 ###

# Table of Contents

  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Acronyms](#acronyms)
  * [1. Modular Chassis Thermalctld architecture](#1-modular-voq-chassis-reference)
  * [2. Tansceiver thermal data in Linecard](#2-sonic-platform-management-and-monitoring)
  * [3. Approaches to send transceiver thermal data](#3-detailed-workflow)
    * [3.1 Send raw optics thermal data from Linecard to Supervisor](#31-send-raw-optics-thermal-data-from-linecard-to-supervisor)
    * [3.2 Process optics thermal data in Linecard send result to Supervisor](#32-process-optics-thermal-data-in-linecard-send-result-to-supervisor)
      
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
 
 #### CHASSIS_STATE_DB Schema for Temperature_Info
 ```
 key                                   = TEMPERATURE_INFO_<card-index>|<Sensor-Name>; 
 ; field                               = value
 temperature_high_alarm                = float;
 temperature_low_alarm                 = float;   
 temperature_high_warning              = float;
 temperature_low_warning               = float;
 temperature                           = float;
 ```

### How it will be done in thermalctld ?


### 3.2 Process optics thermal data in Linecard send result to Supervisor

 This case where thermalctld in each Linecard/module processes thermal data locally and sends the thermal algorithm result to Supervisor CHASSIS_STATE_DB.
 
 The thermalctld daemon in the Linecard will fetch the optical module temperature and thresolds from TRANSCEIVER_DOM_SENSOR and TRANSCEIVER_DOM_THRESHOLD tables in the local STATE_DB. It will process this locally along with other thermal sensor data and send the thermal algorithm result to Supervisor. The Supervisor/thermalctld will use this data as input to cooling algorithm.

 Following schema could be used to store the TEMPERATURE_INFO which is per Linecard module. This will contain attributes like recommended fan speed, any of the sensors which are having high/low alrams etc.
 
 #### CHASSIS_STATE_DB Schema for Temperature_Info
 ```
 key                                   = TEMPERATURE_INFO_<card-index>|THERMAL_ALGO_RESULT; 
 ; field                               = value
 recommended_fan_speed                 = float
 <sensor_name_alarm_type>              = "High/Low"
 <sensor_name_temperature>             = float
 ..
 <sensor_name_alarm_type>              = "High/Low"
 <sensor_name_temperature>             = float
 ```
  
### How it will be done in thermalctld ?


Irrespective of the approach, the above processing could be done by the ThermalMonitor/TemperatureUpdater infrastructure in thermalctld, which does push thermal data from Linecard module to Supervisor.
