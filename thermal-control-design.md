# SONiC Thermal Control Design #

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo      | Initial version                   |
 | 0.2 |             |      Liu Kebo      | Revised after community review    |


  
## 1. Overview

The purpose of Thermal Control is to keep the switch at a proper temperature by using cooling devices, e.g., fan.
Thermal control daemon need to monitor the temperature of devices (CPU, ASIC, optical modules, etc) and the running status of fan. It store temperature values fetched from sensors and thermal device running status to the DB, to make these data available to CLI and SNMP or other apps which interested. 

Thermal control also enforce some environment related polices to help the thermal control algorithm to adjust the switch temperature.     

## 2. Thermal device monitoring

Thermal monitoring function will retrieve the switch device temperatures via platform APIs, platform APIs not only provide the value of the temperature, but also provide the threshold value. The thermal object status can be deduced by comparing the current temperature value against the threshold. If it above the high threshold or under the low threshold, alarm shall be raised.

Besides device temperature, shall also monitoring the fan running status.

Thermal device monitoring will loop at a certain period, 60s can be a good value since usually temperature don't change much in a short period.

### 2.1 Temperature monitoring 

In new platform API ThermalBase() class provides get_temperature(), get_high_threshold(),  get_low_threshold(), get_critical_high_threshold() and get_critical_low_threshold() functions, values for a thermal object can be fetched from them. Warning status can also be deduced. 

For the purpose of feeding CLI/SNMP or telemetry functions, these values and warning status can be stored in the state.  DB schema can be like this:

    ; Defines information for a thermal object
    key                     = TEMPERATURE_INFO|object_name   ; name of the thermal object(CPU, ASIC, optical modules...)
    ; field                 = value
    temperature             = FLOAT                          ; current temperature value
    timestamp               = STRING                         ; timestamp for the temperature fetched
    high_threshold          = FLOAT                          ; temperature high threshold
    critical_high_threshold = FLOAT                          ; temperature critical high threshold
    low_threshold           = FLOAT                          ; temperature low threshold
    critical_low_threshold  = FLOAT                          ; temperature critical low threshold
    warning_status          = BOOLEAN                        ; temperature warning status

These devices shall be included to the temperature monitor list but not limited to: CPU core, CPU pack, ASIC, PSU, Optical Modules, etc.

TEMPERATURE_INFO Table key object_name convention can be "device_name + index"  or device_name if there is no index, like "cpu_core_0", "asic", "psu_2".  Appendix 1 listed all the thermal sensors that supported on Mellanox platform.
    
### 2.2 Fan device monitoring 

In most case fan is the device to cool down the switch when the temperature is rising. Thus to make sure fan running at a proper speed is the key for thermal control.

Fan target speed and speed tolerance was defined, by examining them we can know whether the fan reached at the desired speed.

same as the temperature info, a [table for fan](https://github.com/Azure/SONiC/blob/master/doc/pmon/pmon-enhancement-design.md#153-fan-table) also defined as below:

	; Defines information for a fan
	key                     = FAN_INFO|fan_name              ; information for the fan
	; field                 = value
	presence                = BOOLEAN                        ; presence of the fan
	model                   = STRING                         ; model name of the fan
	serial                  = STRING                         ; serial number of the fan
	status                  = BOOLEAN                        ; status of the fan
	change_event            = STRING                         ; change event of the fan
	direction               = STRING                         ; direction of the fan 
	speed                   = INT                            ; fan speed
	speed_tolerance         = INT                            ; fan speed tolerance
	speed_target            = INT                            ; fan target speed
	led_status              = STRING                         ; fan led status
	timestamp               = STRING                         ; timestamp for the fan info fetched

### 2.3 Syslog for thermal control

If there was warning raised or warning cleared, log shall be generated:

	High temperature warning: PSU 1 current temperature 85C, high threshold 80C！
	High temperature warning cleared, PSU1 temperature restore to 75C, high threshold 80C

If fan broken or become up present, log shall be generated：

	Fan removed warning: Fan 1 was removed from the system, potential overheat hazard!
	Fan removed warning cleared: Fan 1 was inserted.

## 3. Thermal control management

Adjust cooling device according to the current temperature can be very vendor specific and some vendors already have their own implementation. In below Appendix chapter describes a Mellanox implementation. But handle the cooling device according to some predefined policies can be generic, this is part of what Thermal control management will do.

This cooling device control function can be disabled if the vendor have their own implementation in the kernel or somewhere else.

### 3.1 Thermal control management flow

It will be a routing function to check whether the policies was hit an the fan speed need to adjust, and also run vendor specific thermal control algorithm.


Below policies are examples that can be applied:

- Set PWM to full speed if one of PS units is not present 

- Set PWM to full speed if one of FAN drawers is not present or one of tachometers is broken present 

- Set the fan speed to a consant value (60% of full speed) thermal control functions was disabled.

FAN status led and PSU status led shall also be set accordingly when policy meet.

Policy check functions will go through the device status and adjus the fan speed if necessary, these check will be preformed by calling the platform new API.

A thermal control daemon class will be deifined with above functions defined, vendors will be allowed to have their own implementation.

![](https://github.com/keboliu/SONiC/blob/master/images/thermal-control.svg)

### 3.2 Policy management

Policies are defined in a json file for each hwsku, for example, one SKU want to apply below policies:

- Thermal control algorithm control, enabled this hwsku or not, fan speed value to set if not running;

- FAN absence action, suspend the algorithm or not, fan speed value to set;

- PSU absence action, suspend the algorithm or not, fan speed value to set.

- All fans failed/absebce action, power down the  

Below is an example for the policy configuration:

	{
	    "thermal_control_algorithm": {
		"run_at_boot_up": true,
		"fan_speed_when_suspend": 60%
	    },
	    "fan_absence": {
		"action": {
		    "thermal_control_algorithm": "disable",
		    "fan_speed": 100%,
		    "led_color": "red"
		}
	    },
	    "psu_absence": {
		"action": {
		    "thermal_control_algorithm": "disable",
		    "fan_speed": 100%,
		    "led_color": "red"
		}
	    },
	    "all_fan_failed": {
	        "action": {
		    "shutdown_switch": true
		 }
	    }
	}

In this configuration, thermal control algorithm will run on this device; in fan absence situation, the fan speed need to be set to 100%, the thermal control algorithm will be suspended and fan status led shall be set to red ; in psu absence situation, thermal control algorithm will be suspend, fan speed will be set to 100% and psu status led shall be set to red.

During daemon start, this configuration json file will be loaded and parsed, daemon will handle the thermal control algorithm run and fan speed set when predefined policy meet.

## 4. CLI show command for temperature and fan design

### 4.1 New CLI show command for temperature

 adding a new sub command to the "show platform":
 
	admin@sonic# show platform ?
	Usage: show platform [OPTIONS] COMMAND [ARGS]...

	  Show platform-specific hardware info

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  mlnx         Mellanox platform specific configuration...
	  psustatus    Show PSU status information
	  summary      Show hardware platform information
	  syseeprom    Show system EEPROM information
	  temperature  Show device temperature information
	  
out put of the new CLI

    admin@sonic# show platform temperature
    NAME Temperature       Timestamp       High Threshold   Low Threshold    Critical High Threshold   Critical Low Threshold   Warning Status
    ---- -----------  ------------------   ---------------  --------------   ------------------------ ------------------------ ----------------
    CPU      85        20191112 09:38:16        110              -10                 120                        -20                   false
    ASIC     75        20191112 09:38:16        100               0                  110                        -10                   false

An option '--major' provided by this CLI to only print out major device temp, if don't want show all of sensor temperatures.
Major devices are CPU pack, cpu cores, ASIC and optical modules.

### 4.2 New show CLI for fan status

We don't have a CLI for fan status getting yet, new CLI for fan status could be like below, it's adding a new sub command to the "show platform":

	admin@sonic# show platform ?
	Usage: show platform [OPTIONS] COMMAND [ARGS]...

	  Show platform-specific hardware info

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  fanstatus  Show fan status information
	  mlnx       Mellanox platform specific configuration...
	  psustatus  Show PSU status information
	  summary    Show hardware platform information
	  syseeprom  Show system EEPROM information
The output of the command is like below:

	admin@sonic# show platform fanstatus
	FAN    Speed      Direction      Timestamp
	-----  ---------  ---------  -----------------
	FAN 1  12919 RPM  Intake     20191112 09:38:16
	FAN 2  13043 RPM  Exhaust    20191112 09:38:16


## 5. Potential ehhancement for Platform API
1. Why can't we propose different change events for different cpu/fan/optics?
2. Verbose on API definition on threshold levels about Average/Max/Snapshot.
3. Is there any API exposed for fanTray contain more than one fan?

## Appendix

## 1.Mellanox platform thermal sensors list

On Mellanox platform we have below thermal sensors that will be monitored by the thermal control daemons, not all of the Mellanox platform include all of them, some platform maybe only have a subset of these thermal sensors.

        cpu_core_x : "CPU Core x Temp", 
        cpu_pack : "CPU Pack Temp",
        modules_x : "xSFP module x Temp",
        psu_x : "PSU-x Temp",
        gearbox_x : "Gearbox x Temp"
        asic : "Ambient ASIC Temp",
        port : "Ambient Port Side Temp",
        fan : "Ambient Fan Side Temp",
        comex : "Ambient COMEX Temp",
        board : "Ambient Board Temp"
 

## 2.Mellanox thermal control implementation

### 2.1 Mellanox thermal Control framework

Mellanox thermal monitoring measure temperature from the ports and ASIC core. It operates in kernel space and binds PWM(Pulse-Width Modulation) control with Linux thermal zone for each measurement device (ports & core). The thermal algorithm uses step_wise policy which set FANs according to the thermal trends (high temperature = faster fan; lower temperature = slower fan). 

More detail information can refer to Kernel documents https://www.kernel.org/doc/Documentation/thermal/sysfs-api.txt
and Mellanox HW-management package documents: https://github.com/Mellanox/hw-mgmt/tree/master/Documentation

### 2.2 Components

- The cooling device is an actual functional unit for cooling down the thermal zone: Fan.

- Thermal instance describes how cooling devices work at certain trip point in the thermal zone.

- Governor handles the thermal instance not thermal devices. Step_wise governor sets cooling state based on thermal trend (STABLE, RAISING, DROPPING, RASING_FULL, DROPPING_FULL). It allows only one step change for increasing or decreasing at decision time. Framework to register thermal zone and cooling devices:

- Thermal zone devices and cooling devices will work after proper binding. Performs a routing function of generic cooling devices to generic thermal zones with the help of very simple thermal management logic.

### 2.3 Algorithm

Use step_wise policy for each thermal zone. Set the fan speed according to different trip points. 

### 2.4 Trip points

a series of trip point is defined to trigger fan speed manipulate.

 |state   |Temperature value(Celsius) |PWM speed                  |Action                                    |
 |:------:|:-------------------------:|:-------------------------:|:-----------------------------------------|
 |Cold    |      t < 75 C    | 20%        |   Do nothing                             |
 |Normal  |    75 <= t < 85  | 20% - 40%  |   keep minimal speed|
 |High    |  85 <= t < 105   | 40% - 100% | adjust the fan speed according to the trends|
 |Hot     |  105 <= t < 110  | 100%       | produce warning message                     |
 |Critical|  t >= 110        | 100%       |  shutdown |

