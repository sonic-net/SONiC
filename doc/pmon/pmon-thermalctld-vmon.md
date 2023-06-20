# SONiC PMON Voltage Monitoring Enhancement #


### Revision 1.0 

## Table of Content 
1. [Scope](#Scope)
2. [Definitions](#Definitions/Abbreviations)
3. [Overview](#Overview)
3. [Requirements](#Requirements)
4. [High Level Design](#High-Level-Design)
5. [CLI](#CLI-Enhancements)
7. [Test](#Testing-Considerations)



### Scope  

This document covers the support for monitoring voltage sensor devices in SONiC. 

### Definitions/Abbreviations 

PMON - Platform Monitor container in SONiC.

PSU - Power Supply Unit

Voltage Sensor - Sensor device which can report a voltage measurement in the system.

### Overview 

Modern hardware systems have a number of sensor and control devices. Voltage and current sensor devices can measure and in some cases control the voltages on the boards. Many systems have a number of such devices to distribute power across the different parts of the system including motherboard, daughterboards etc. These devices should be monitored to alert the operator about any failures that might affect the operation of the system. This document provides an overview of how the voltage sensors can be modeled and monitored in SONiC.


### Requirements

This HLD covers

* Discovery of voltage sensor devices in the system
* Monitoring the voltage sensor devices periodically and update that data in Redis DB
* Raise/Clear alarms if the voltage sensor devices indicate readings which are unexpected and clear them if they return to a good state.

This HLD does not cover

* An automated recovery action that system might take as a result of a fault reported by the voltage sensor device. A network management system may process the alarms and take recvoery action as it sees fit.


### High Level Design 

The proposal for monitoring voltage sensor devices is to enhance the PMON ThermalCtld Daemon functionality. ThermalCtld monitors the temperature sensors and uses that information to control fan speed in the system. For this purpose ThermalCtld discovers the temperature sensor devices and periodically polls them to collect their information. This mechanism can be extended to monitoring the voltage sensor devices as well. 

ThermalCtld will discover the voltage sensor devices in the system on bootup and update their information in StateDB. Subsequently it will periodically poll the voltage sensor devices and publish the readings in RedisDB. If the sensor device readings cross the minor/major/critical thresholds, syslogs will be generated to indicate to the operator about the alarm condition. If the sensor reports normal data in a subsequent poll, another syslog will be generated to indicate that the fault condition is cleared.

CLI is provided to display the voltage sensor devices, their current measurements and threshold values. 

Platform APIs will provide 

* List of voltage sensors devices in the system
* Way to read the voltage sensor devices

The following SONiC repositories will have changes

#### sonic-platform-daemons	

Thermaltcld script will retrieve voltage sensors data from the platform on coming up and poll for refreshing the data periodically.
	
#### sonic-platform-common

Chassis Base class will be enhanced with prototype methods for retrieving number of voltage sensors and voltage sensor objects.

Module base class will also be enhanced with similar methods for retrieving voltage sensors present on the modules.

A new base class - VsensorBase - is introduced for voltage sensor objects. The class will have methods to retrieve threshold information, sensor value and min/max recorded values from the sensor.
	
#### sonic-utilities
	
CLI is introduced to retrieve and display voltage sensor data from State DB.


### CLI Enhancements 

Following CLI is introduced to display the Voltage Sensor devices.

	root@sonic:/home/cisco# show platform voltage
	          Sensor    Voltage(mV)    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU0            750        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU1            750        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU2            750        852       684             872            664      False  20230204 11:35:22
	...
	

#### Configuration and Management

At this point, there is no configuration requirement for this feature. If the platform does not specify any voltage sensors in the thermal_zone.yaml file, there will be no voltage sensor information reported.

It is advised to monitor the voltage sensor alarms and use that to debug and identify any issues in the system. In the event, a voltage sensor crosses a high or low threshold, syslogs will be raised indicating the alarm.

	Feb  4 09:11:24.669278 sonic WARNING pmon#thermalctld: High voltage warning: VP0P75_CORE_NPU3 current voltage 750C, high threshold 720C

The alarm condition will also be visible in the CLI ouput.

	e.g 
	root@sonic:/home/cisco# show platform voltage
	          Sensor    Voltage(mV)    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU3            750        720       684             720            664       True  20230204 11:35:22
	

#### Warmboot and Fastboot Design Impact  

Warmboot and Fastboot should not be impacted by this feature. On PMON container restart, the voltage monitoring should restart the same way as on boot.

### Testing Considerations  

Unit test cases cover the CLI and voltage monitoring aspect. 

Voltage threshold crossing can be simulated by adjusting the thresholds in thermal_zone.yaml file. This can be used to check syslog and alarm indications.

#### Unit Test cases  

TBD