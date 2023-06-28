# SONiC PMON Sensor Monitoring Enhancement #


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

This document covers the support for monitoring voltage and current sensor devices in SONiC. 

### Definitions/Abbreviations 

PMON - Platform Monitor container in SONiC.

PSU - Power Supply Unit

Voltage Sensor - Sensor device which can report a voltage measurement in the system.

Current Sensor - Sensor device which can report current measurement in the system.

Altitude Sensor - Sensor device which can report the altitude of the system.


### Overview 

Modern hardware systems have many different types of sensors and control devices. Voltage sensor devices can measure and in some cases control the voltages on the boards. Current sensor devices can measure current. It is also possible to have other types of sensors such as Altitude Sensors etc. These devices can report measurements from different parts of the system which are useful for monitoring system health. For example, voltage controller devices distribute power across different parts of the system such as  motherboard, daughterboards etc. and can report voltage measurements from there. Often these devices can report under-voltage/over-voltage faults which should be monitored to alert the operator about any power related failures in the system. This document provides an overview for monitoring voltage and current sensors in SONiC. The solution proposed in this document can be enhanced for other types of sensors as well.

Note that temperature sensor devices are managed via SONiC ThermalCtlD daemon today. At this point there is no change proposed for ThermalCtlD. This proposed design can be used for voltage, current and other types of sensors.


### Requirements

This HLD covers

* Discovery of voltage and current sensor devices in the system
* Monitoring the sensor devices periodically and update that data in Redis DB
* Raise/Clear alarms if the sensor devices indicate readings which are unexpected and clear them if they return to a good state.
* A framework for adding new sensor types in future

This HLD does not cover

* An automated recovery action that system might take as a result of a fault reported by the voltage sensor device. A network management system may process the alarms and take recvoery action as it sees fit.


### High Level Design 

The proposal for monitoring sensor devices is to create a new SensorMon daemon. SensorMon will use API provided by platform to discover the sensor devices. It will periodically poll the devices to refresh the sensor information and update the readings in StateDB.

If the sensor device readings cross the minor/major/critical thresholds, syslogs will be generated to indicate to the operator about the alarm condition. If the sensor reports normal data in a subsequent poll, another syslog will be generated to indicate that the fault condition is cleared.

CLIs are provided to display the sensor devices, their measurements, threshold values and if they are reporting an alarm.

Platform APIs will provide 

* List of sensors devices of a specific type in the system
* Way to read the sensor information

The following SONiC repositories will have changes

#### sonic-platform-daemons	

SensorMon will be a new daemon that will run in PMON container. It will retrieve a list of sensors of different sensor types from the platform during initialization. Subsequently, it will poll the sensor devices on a periodic basis and update their measurments in StateDb. SemsorMon will also raise syslogs on alarm conditions. 

	
#### sonic-platform-common

Chassis Base class will be enhanced with prototype methods for retrieving number of sensors and sensor objects of a specific type.

Module base class will also be enhanced with similar methods for retrieving sensors present on the modules.

New base classes will be introduced for new sensor types.

VsensorBase is introduced for voltage sensor objects. 
IsensorBase is introdued for current sensor objects.

The classes will have methods to retrieve threshold information, sensor value and min/max recorded values from the sensor.
	
#### sonic-utilities
	
CLIs are introduced to retrieve and display sensor data from State DB for different sensor types. CLIs are described in the next section.


### CLI Enhancements 

Following CLI is introduced to display the Voltage and Current Sensor devices.

	root@sonic:/home/cisco# show platform voltage
	          Sensor    Voltage(mV)    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU0            750        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU1            750        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU2            750        852       684             872            664      False  20230204 11:35:22
	...
	
	root@sonic:/home/cisco# show platform current
	        Sensor    Current(mA)    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	--------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	POL_CORE_N0_I0          25000      30000     18000           28000          15000      False  20230212 11:18:28
	POL_CORE_N0_I1          21562      30000     18000           28000          15000      False  20230212 11:18:28
	POL_CORE_N0_I2          22250      30000     18000           28000          15000      False  20230212 11:18:28


	

#### Configuration and Management

At this point, there is no configuration requirement for this feature. 

If the SensorMon daemon is not desired to be run in the system, an entry can be added to  pmon_daemon_control.json to exclude it from running in the system.

It is advised to monitor the sensor alarms and use that to debug and identify any issues in the system. In the event, a sensor crosses a high or low threshold, syslogs will be raised indicating the alarm.

	Feb  4 09:11:24.669278 sonic WARNING pmon#sensormon: High voltage warning: VP0P75_CORE_NPU3 current voltage 750C, high threshold 720C

The alarm condition will also be visible in the CLI ouput.

	e.g 
	root@sonic:/home/cisco# show platform voltage
	          Sensor    Voltage(mV)    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU3            750        720       684             720            664       True  20230204 11:35:22
	

#### Warmboot and Fastboot Design Impact  

Warmboot and Fastboot should not be impacted by this feature. On PMON container restart, the sensor monitoring should restart the same way as on boot.

### Testing Considerations  

Unit test cases cover the CLI and sensor monitoring aspect. 


#### Unit Test cases  

TBD