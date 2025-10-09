# SONiC Chassis Platform Optics Thermal Management & Monitoring #

### Rev 1.1 ###

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
  -- general architecture

## 2. Transceiver thermal data in Linecard
  -- how and which tables the temperature information and threasholds are stored currently

## 3. Approaches to send transceiver hermal data from Linecard to Supervisor
  -- Find currently how we do  

### 3.1 Send raw optics thermal data from Linecard to Supervisor

 This case where thermalctld in each Linecard/module **don't** process thermal data locally, instead just send each optics Temperature_info(along with the other thermals) to Supervisor CHASSIS_STATE_DB. The Supervisor/thermalctld use this directly as input to cooling algorithm.
 
 Following schema could be used to store the TEMPERATURE_INFO in the CHASSIS_STATE_DB. The Sensor-Name will be interface name.
 
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
  -- will it be stored locally ?
  -- what is the table it will be stored in Supervisor 
  -- which DB it will be stored in Supervisor
  -- Who controls the latency in which this data is pushed to Supervisor
  --  What can be streamed from LC/SUP ?

### 3.2 Process optics thermal data in Linecard, send result to Supervisor

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
  --  Check how it is stored locally
  --  How to specifiy parameters, vendor specific parameters
  --  What can be streamed from LC/SUP ? It is actually streamed already
  --   

Irrespective of the approach, the above processing could be done by the ThermalMonitor/TemperatureUpdater infrastructure in thermalctld, which does push thermal data from Linecard module to Supervisor.
