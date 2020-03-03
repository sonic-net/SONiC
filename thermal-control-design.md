# SONiC Thermal Control Design #

### Rev 0.3 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo      | Initial version                   |
 | 0.2 |             |      Liu Kebo      | Revised after community review    |
 | 0.3 |             |      Junchao Chen  | Revised after code review         |


  
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
	direction               = STRING                         ; direction of the fan 
	speed                   = INT                            ; fan speed
	speed_tolerance         = INT                            ; fan speed tolerance
	speed_target            = INT                            ; fan target speed
	led_status              = STRING                         ; fan led status
	timestamp               = STRING                         ; timestamp for the fan info fetched

### 2.3 Syslog for thermal control

If there was warning raised or warning cleared, log shall be generated:

	High temperature warning: PSU 1 current temperature 85C, high threshold 80C！
	High temperature warning cleared, PSU 1 temperature restore to 75C, high threshold 80C

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

Policy check functions will go through the device status and adjust the fan speed if necessary, these check will be preformed by calling the platform new API.

A thermal control daemon class will be deifined with above functions defined, vendors will be allowed to have their own implementation.

![](https://github.com/keboliu/SONiC/blob/master/images/thermal-control.svg)

### 3.2 Policy management

Policies are defined in a json file for each hwsku, for example, one SKU want to apply below policies:

- Thermal control algorithm control, enabled this hwsku or not, fan speed value to set if not running;

- Thermal information need to be collected;

- FAN absence action, suspend the algorithm or not, fan speed value to set;

- PSU absence action, suspend the algorithm or not, fan speed value to set;

- All FAN and PSU presence action, suspend the algorithm or not, fan speed value to set.

Below is an example for the policy configuration:

```
{   
    "thermal_control_algorithm": {
        "run_at_boot_up": "false",
        "fan_speed_when_suspend": "60"
    },
    "info_types": [
        {
            "type": "fan_info"
        },
        {
            "type": "psu_info"
        },
        {
            "type": "chassis_info"
        }
    ],
    "policies": [
        {
            "name": "any fan absence",
            "conditions": [
                {
                    "type": "fan.any.absence"
                }
            ],
            "actions": [
                {
                    "type": "thermal_control.control",
                    "status": "false"
                },
                {
                    "type": "fan.all.set_speed",
                    "speed": "100"
                }
            ]
        },
        {
            "name": "any psu absence",
            "conditions": [
                {
                    "type": "psu.any.absence"
                }
            ],
            "actions": [
                {
                    "type": "thermal_control.control",
                    "status": "false"
                },
                {
                    "type": "fan.all.set_speed",
                    "speed": "100"
                }
            ]
        },
        {
            "name": "all fan and psu presence",
            "conditions": [
                {
                    "type": "fan.all.presence"
                },
                {
                    "type": "psu.all.presence"
                }
            ],
            "actions": [
                {
                    "type": "fan.all.set_speed",
                    "speed": "60"
                }
            ]
        }
    ]
}
```

In this configuration, thermal control algorithm will run on this device; in fan absence situation, the fan speed need to be set to 100%, the thermal control algorithm will be suspended; in psu absence situation, thermal control algorithm will be suspend, fan speed will be set to 100%.

During daemon start, this json configuration file will be loaded and parsed, daemon will handle the thermal control algorithm run and fan speed set when predefined policy meet.

### 3.3 Policy implementation

A few Python class will be added to sonic-platform-common to support thermal policy.

- ThermalManagerBase is responsible for initializing thermal algorithm, loading the json configuration file, collecting thermal information and performing thermal policies. ThermalManagerBase is a singleton.
- ThermalPolicy stores thermal conditions and thermal actions. For a ThermalPolicy instance, once all thermal conditions meet, all its thermal actions will be executed.
- ThermalJsonObject provides abstract interface "load_from_json" to allow derived class de-serialize from json configuration file.
- ThermalPolicyInfoBase inherits ThermalJsonObject, provides abstract interface "collect" to allow derived class collect information which will be used by thermal conditions and thermal actions.
- ThermalPolicyConditionBase inherits ThermalJsonObject, provides abstract interface "is_match" to allow vendors define their own thermal conditions.
- ThermalPolicyActionBase inherits ThermalJsonObject, provides abstract interface "execute" to allow vendors trigger their own thermal actions.

#### 3.3.1 Thermal condition implementation

To implement a concrete thermal condition class, vendor need inherit from ThermalPolicyConditionBase and implement the "is_match" and "load_from_json" interfaces. For example:

```python
@thermal_json_object('my.condition.name')
class MyCondition(ThermalPolicyConditionBase):
    def __init__(self):
        self.member1 = None
        self.member2 = None

    def is_match(self, thermal_info_dict):
        # the thermal_info_dict argument is a dictionary of concrete ThermalPolicyInfoBase instances.
        # if bad:
        #     return True
        # else:
        #     return False

    def load_from_json(self, json_obj):
        self.member1 = json_obj['member1']
        self.member2 = json_obj['member1']
```

And the json configuration for MyCondition class is like:

```json
{
    "type": "my.condition.name",
    "member1": "1",
    "member2": "true"
}
```

The decorate "thermal_json_object" will register this new thermal condition type to a type dictionary with name "my.condition.name" so that this class can be de-serialized from json configuration.

#### 3.3.2 Thermal action implementation

To implement a concrete thermal action class, vendor need inherit from ThermalPolicyActionBase and implement the "execute" and "load_from_json" interfaces. For example:

```python
@thermal_json_object('my.action.name')
class MyAction(ThermalPolicyActionBase):
    def __init__(self):
        self.speed = None

    def execute(self, thermal_info_dict):
        # the thermal_info_dict argument is a dictionary of concrete ThermalPolicyInfoBase instances.
        fan_info_obj = thermal_info_dict['fan_info']
        for fan in fan_info_obj.get_presence_fans():
            fan.set_speed(self.speed)

    def load_from_json(self, json_obj):
        self.speed = json_obj['speed']
```

And the json configuration for MyAction class is like:

```json
{
    "type": "my.action.name",
    "speed": "60"
}
```

The decorate "thermal_json_object" will register this new thermal action type to a type dictionary with name "my.action.name" so that this class can be de-serialized from json configuration.

#### 3.3.3 Thermal information implementation

To implement a concrete thermal information class, vendor need inherit from ThermalPolicyInfoBase and implement the "collect" and "load_from_json" interfaces. For example:


```python
@thermal_json_object('my.info.name')
class MyInfo(ThermalPolicyInfoBase):
    def __init__(self):
        self.absence_fan = None
        self.presence_fan = None

    def collect(self, chassis):
        self.absence_fan = []
        self.presence_fan = []
        for fan in chassis.get_all_fans():
            if fan.get_presence():
                self.presence_fan.append(fan)
            else:
                self.absence_fan.append(fan)

    def load_from_json(self, json_obj):
        pass
```

And the json configuration for MyInfo class is like:

```json
{
    "type": "my.info.name"
}
```

The decorate "thermal_json_object" will register this new thermal information type to a type dictionary with name "my.info.name" so that this class can be de-serialized from json configuration.

After define concrete thermal condition, thermal action and thermal information class, the json configuration can use them like this:

```json
{   
    "thermal_control_algorithm": {
        "run_at_boot_up": "false",
        "fan_speed_when_suspend": "60"
    },
    "info_types": [
        {
            "type": "my.info.name"
        }
    ],
    "policies": [
        {
            "name": "my policy",
            "conditions": [
                {
                    "type": "my.condition.name",
                    "member1": "1",
                    "member2": "true"
                }
            ],
            "actions": [
                {
                    "type": "my.action.name",
                    "speed": "60"
                }
            ]
        }
    ]
}
```

Once ThermalManagerBase loads this configuration file, it will de-serialize one MyInfo object, one ThermalPolicy object which contains one MyCondition object and one MyAction object. ThermalManagerBase will call MyInfo.collect every 60 seconds, and detect if MyCondition.is_match returns True, if MyCondition.is_match returns True, MyAction.execute will be called. This allow vendor to take different actions according to different conditions. Vendor can also define thermal information to assist actions and conditions.


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
    NAME Temperature       Timestamp           High Th          Low Th           Crit High Th             Crit Low Th            Warning Status
    ---- -----------  ------------------   ---------------  --------------   ------------------------ ------------------------ ----------------
    CPU      85        20191112 09:38:16        110              -10                 120                        -20                   False
    ASIC     75        20191112 09:38:16        100               0                  110                        -10                   False


### 4.2 New show CLI for fan status

We don't have a CLI for fan status getting yet, new CLI for fan status could be like below, it's adding a new sub command to the "show platform":

	admin@sonic# show platform ?
	Usage: show platform [OPTIONS] COMMAND [ARGS]...

	  Show platform-specific hardware info

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  fan        Show fan status information
	  mlnx       Mellanox platform specific configuration...
	  psustatus  Show PSU status information
	  summary    Show hardware platform information
	  syseeprom  Show system EEPROM information
The output of the command is like below:

	admin@sonic# show platform fan
	FAN    Speed      Direction  Presence     Status  Timestamp
	-----  ---------  ---------  -----------  ------  -----------------
	FAN 1  85%        Intake     Present      OK      20191112 09:38:16
	FAN 2  60%        Exhaust    Not Present  Not OK  20191112 09:38:16


## 5. Fan led management

In current implementation, fan led management API is based on fan object. However, in many hardware platform, multiple fans are put in a fan drawer, they share one fan led. In such case, to control fan led in a fan object might cause problem. For example, one fan drawer has fan1 and fan2, they share a fan led, fan1 is broken and set led to red via fan1 object, then fan2 just recovers from a bad state and set led to green via fan2 object, the final fan led state will be green which is incorrect. To avoid confusing user, a new abstract class FanDrawerBase is added to sonic_platform_common and vendors should implement it. The FanDrawerBase class will look like:

```python

class FanDrawerBase(device_base.DeviceBase):
    def get_num_fans(self):
        raise NotImplementedError

    def get_all_fans(self):
        raise NotImplementedError

    def set_status_led(self, color):
        raise NotImplementedError

    def get_status_led(self, color):
        raise NotImplementedError

```

The fan drawer object should follow:

- If there are fans without drawer, we still add a drawer object for each of fan, and consider the drawer only has one fan.
- If one fan drawer has more than one fan, drawer need to have internal logic to judge led color according to all its fan status, this is upon vendor’s implementation.
- Thermal control daemon will go through all the drawer and then go though all the fans inside the drawer.
- In the situation when need to set led, thermal control daemon will call fan led set API as well as it’s drawer’s led set api, vendor’s led implementation need to make sure there is no conflict or overwrite case.

Existing platform API need changes:

- Add two new member functions "get_num_fan_drawers" and "get_all_fan_drawers" to ChassisBase, vendor need to implement these two new functions to properly initialize chassis object with fan drawer objects.

## 6. Potential ehhancement for Platform API
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

