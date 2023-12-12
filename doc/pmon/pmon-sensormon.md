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

Linux does provide some support of voltage and current sensor monitoring using lmsensors/hwmon infrastructure. However there are a few limitations with that

- Devices not supported with Hwmon are not covered
- Simple devices which donot have an inbuilt monitoring functions do not generate any alarms
- Platform specific thresholds for monitoring are not available

The solution proposed in this document tries to address these limitations by extending the coverage to a larger set of devices and providing platform specific thresholds for sensor monitoring.


### Requirements

This HLD covers

* Discovery of voltage and current sensor devices in the system
* Monitoring the sensor devices periodically and update that data in Redis DB
* Raise/Clear alarms if the sensor devices indicate readings which are unexpected and clear them if they return to a good state.
* Report sensor alarm conditions in system health
* Enable such sensors in Entity MIB
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

SensorMon will be a new daemon that will run in PMON container. It will retrieve a list of sensors of different sensor types from the platform during initialization. Subsequently, it will poll the sensor devices on a periodic basis and update their measurments in StateDb. SensorMon will also raise syslogs on alarm conditions. 

Following is the DB schema for voltage and current sensor data.

##### Voltage Sensor StateDb Schema

	; Defines information for a voltage sensor
	key                     = VOLTAGE_INFO|sensor_name       ; Voltage sensor name
	; field                 = value
	voltage                 = float                          : Voltage measurement
	unit                    = string                         ; Unit for the measurement
	high_threshold          = float                          ; High threshold 
	low_threshold           = float                          ; Low threshold 
	critical_high_threshold = float                          ; Critical high threshold
	critical_low_threshold  = float                          ; Critical low threshold
	warning_status          = boolean                        ; Sensor value in range
	timestamp               = string                         ; Last update time
	maximum_voltage         = float                          ; Maximum recorded measurement
	minimum_voltage         = float                          ; Mininum recorded measurement

##### Current Sensor StateDb Schema

	; Defines information for a current sensor
	key                     = CURRENT_INFO|sensor_name       ; Current sensor name
	; field                 = value
	current                 = float                          : Current measurement
	unit                    = string                         ; Unit for the measurement
	high_threshold          = float                          ; High threshold 
	low_threshold           = float                          ; Low threshold 
	critical_high_threshold = float                          ; Critical high threshold
	critical_low_threshold  = float                          ; Critical low threshold
	warning_status          = boolean                        ; Sensor value in range
	timestamp               = string                         ; Last update time
	maximum_current         = float                          ; Maximum recorded measurement
	minimum_current         = float                          ; Mininum recorded measurement
	
		
#### sonic-platform-common

Chassis Base class will be enhanced with prototype methods for retrieving number of sensors and sensor objects of a specific type.

Module base class will also be enhanced with similar methods for retrieving sensors present on the modules.

New base classes will be introduced for new sensor types.

VsensorBase is introduced for voltage sensor objects. 
IsensorBase is introdued for current sensor objects.

The classes will have methods to retrieve threshold information, sensor value and min/max recorded values from the sensor.
	
#### sonic-utilities
	
CLIs are introduced to retrieve and display sensor data from State DB for different sensor types. CLIs are described in the next section.

#### sonic-buildimage

The CLI "show system-health" should report sensor fault conditions. Hardware health check script will need enhancement to retrieve sensor data from StateDB. 

#### sonic-snmpagent

Voltage and Current sensors should be available in Entity MIB. Entity MIB implementation will need an enhancement to retrieve voltage and current sensors from the state DB.

### CLI Enhancements 

Following CLI is introduced to display the Voltage and Current Sensor devices.

	root@sonic:/home/cisco# show platform voltage
	          Sensor       Voltage    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU0         750 mV        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU1         750 mV        852       684             872            664      False  20230204 11:35:21
	VP0P75_CORE_NPU2         750 mV        852       684             872            664      False  20230204 11:35:22
	
	...
	
	root@sonic:/home/cisco# show platform current
	        Sensor        Current    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	--------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	POL_CORE_N0_I0       25000 mA      30000     18000           28000          15000      False  20230212 11:18:28
	POL_CORE_N0_I1       21562 mA      30000     18000           28000          15000      False  20230212 11:18:28
	POL_CORE_N0_I2       22250 mA      30000     18000           28000          15000      False  20230212 11:18:28


	

#### Configuration and Management

At this point, there is no configuration requirement for this feature. 

If the SensorMon daemon is not desired to be run in the system, an entry can be added to  pmon_daemon_control.json to exclude it from running in the system.

It is advised to monitor the sensor alarms and use that to debug and identify any issues in the system. In the event, a sensor crosses a high or low threshold, syslogs will be raised indicating the alarm.

	FJul 27 08:26:32.561330 sonic WARNING pmon#sensormond: High voltage warning: VP0P75_CORE_NPU2 current voltage 880mV, high threshold 856mV

The alarm condition will be visible in the CLI ouputs for sensor data and system health.

	e.g 
	root@sonic:/home/cisco# show platform voltage
	          Sensor        Voltage    High TH    Low TH    Crit High TH    Crit Low TH    Warning          Timestamp
	----------------  -------------  ---------  --------  --------------  -------------  ---------  -----------------
	VP0P75_CORE_NPU2         880 mV        720       684             720            664       True  20230204 11:35:22
	
	root@sonic:/home/cisco# show system-health detail
	System status summary
  	...
  	  Hardware:
       Status: Not OK
       Reasons: Voltage sensor VP0P75_CORE_NPU2 measurement 880 mV out of range (679,856)
    	...
    	VP0P75_CORE_NPU2            Not OK    voltage
    	...


##### Platform Sensors Configuration

Sensormond will use the platform APIs for retrieving platform sensor information. However, for platforms with only file-system/sysfs based drivers, a simple implementation is provided wherein the platform can specify the sensor information for the board and any submodules (such as fabric cards) in a data file and Sensormond can use that for finding sensors and monitoring them. 

The file system/Sysfs based platform sensor information can be provided using a yaml file. The yaml file shall have the following format.

 	
	sensors.yaml
      
    voltage_sensors:
      - name : <sensor name>
          sensor: <sysfs path>
          high_thresholds: [ <critical>, <major>, <minor> ]
          low_thresholds: [ <critical>, <major>, <minor> ]
        ...
      
    current_sensors:
      - name : <sensor name>
          sensor: <sysfs path>
          high_thresholds: [ <critical>, <major>, <minor> ]
          low_thresholds: [ <critical>, <major>, <minor> ]
        ...
      
    <module_name>:
      voltage_sensors:
        - name: <sensor name>
            sensor: <sysfs path>
            high_thresholds: [ <critical>, <major>, <minor> ]
            low_thresholds: [ <critical>, <major>, <minor> ]
          ...
 
      current_sensors:
        - name: <sensor name>
            sensor: <sysfs path>
            high_thresholds: [ <critical>, <major>, <minor> ]
            low_thresholds: [ <critical>, <major>, <minor> ]
          ...




##### PDDF Support

SONiC PDDF provides a data driven framework to access platform HW devices. PDDF allows for sensor access information to be read from platform specific json files. PDDF support can be added for voltage and current sensors which can be retrieved by Sensormon.
 

#### Warmboot and Fastboot Design Impact  

Warmboot and Fastboot should not be impacted by this feature. On PMON container restart, the sensor monitoring should restart the same way as on boot.

### Testing Considerations  

Unit test cases cover the CLI and sensor monitoring aspects. All SONiC common repos will have unit tests and meet code coverage requirements for the respective repos. In addition SONiC management tests will cover the feature on the target.

### Feature availability

The core implementation for the daemon process is available at this time along with the HLD. This includes changes in the following repos

* Sonic-platform-daemons
* sonic-platform-common
* sonic-utilities
* sonic-buildimage
* sonic-snmpagent

SONiC management test cases and PDDF support will be available in the next phase of development.
