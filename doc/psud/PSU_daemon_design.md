# SONiC PSU Daemon Design #

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                       |
 |:---:|:-----------:|:------------------:|------------------------------------------|
 | 0.1 |             |      Chen Junchao  | Initial version                          |
 | 0.2 |   07/22     |      Or Farfara    | add input current, voltage and max power |


## 1. Overview

The purpose of PSU daemon is to collect platform PSU data and trigger proper actions if necessary. Major functions of psud include:

- Collect constant PSU data during daemon boot up, such as PSU number.
- Collect variable PSU data periodically.
- Monitor PSU event, set LED color and trigger syslog according to event type.

## 2. PSU data collection

PSU daemon data collection flow diagram:

![](https://github.com/Azure/SONiC/blob/master/doc/pmon/daemon-flow.svg)

Now psud collects PSU data via platform API, and it also support platform plugin for backward compatible. All PSU data will be saved to redis database for further usage.

## 3. DB schema for PSU

PSU number is stored in chassis table. Please refer to this [document](https://github.com/Azure/SONiC/blob/master/doc/pmon/pmon-enhancement-design.md), section 1.5.2.

PSU information is stored in PSU table:

	; Defines information for a psu
	key                     = PSU_INFO|psu_name              ; information for the psu
	; field                 = value
	presence                = BOOLEAN                        ; presence of the psu
	model                   = STRING                         ; model name of the psu
	serial                  = STRING                         ; serial number of the psu
	status                  = BOOLEAN                        ; status of the psu
	change_event            = STRING                         ; change event of the psu
	fan                     = STRING                         ; fan_name of the psu
	led_status              = STRING                         ; led status of the psu
	input_voltage           = STRING                         ; input voltage of the psu
	input_current           = STRING                         ; input current of the psu
	max_power               = STRING                         ; power capacity of the psu

Now psud only collect and update "presence" and "status" field.

## 4. PSU command

There is a sub command "psustatus" under "show platform"

```
admin@sonic:~$ show platform ?
Usage: show platform [OPTIONS] COMMAND [ARGS]...

  Show platform-specific hardware info

Options:
  -?, -h, --help  Show this message and exit.

Commands:
  fan          Show fan status information
  firmware     Show firmware status information
  mlnx         Show Mellanox platform information
  psustatus    Show PSU status information
  ssdhealth    Show SSD Health information
  summary      Show hardware platform information
  syseeprom    Show system EEPROM information
  temperature  Show device temperature information\
```

The current output for "show platform psustatus" looks like:

```
admin@sonic:~$ show platform psustatus
PSU    Status
-----  --------
PSU 1  OK
PSU 2  OK
```

## 5. PSU LED management

The purpose of PSU LED management is to notify user about PSU event by PSU LED or syslog. Current PSU daemon psud need to monitor PSU event (PSU voltage out of range, PSU too hot) and trigger proper actions if necessary.

### 5.1 PSU event definition

We define a few abnormal PSU events here. When any PSU event happens, syslog should be triggered with "Alert Message", PSU LED should be set to "PSU LED color"; when any PSU restores from previous abnormal state, syslog should be triggered with "Recover Message". PSU LED should be set to green only if there is no any abnormal PSU event happens.

#### 5.1.1 PSU voltage out of range

    Alert Message: PSU voltage warning: <psu_name> voltage out of range, current voltage=<current_voltage>, valid range=[<min_voltage>, <max_voltage>].

    PSU LED color: red.

    Recover Message: PSU voltage warning cleared: <psu_name> voltage is back to normal.

#### 5.1.2 PSU temperature too hot

    Alert Message: PSU temperature warning: <psu_name> temperature too hot, temperature=<current_temperature>, threshold=<threshold>.

    PSU LED color: red.

    Recover Message: PSU temperature warning cleared: <psu_name> temperature is back to normal.

#### 5.1.3 Power absence

    Alert Message: Power absence warning: <psu_name> is out of power. 

    PSU LED color: red.

    Recover Message: Power absence warning cleared: <psu_name> power is back to normal.

#### 5.1.4 PSU absence

    Alert Message: PSU absence warning: <psu_name> is not present. 

    PSU LED color: red. (PSU LED might not be available at this point)

    Recover Message: PSU absence warning cleared: <psu_name> is inserted back.

### 5.2 Platform API change

Some abstract member methods need to be added to [psu_base.py](https://github.com/Azure/sonic-platform-common/blob/master/sonic_platform_base/psu_base.py) and vendor should implement these methods.

```python

class PsuBase(device_base.DeviceBase):
    ...
    def get_temperature(self):
        raise NotImplementedError

    def get_temperature_high_threshold(self):
        raise NotImplementedError

    def get_voltage_high_threshold(self):
        raise NotImplementedError

    def get_voltage_low_threshold(self):
        raise NotImplementedError
    ...

```

### 6. PSU daemon flow

Supervisord takes charge of this daemon. This daemon will loop every 3 seconds and get the data from psuutil/platform API and then write it the Redis DB.

- The psu_num will store in "chassis_info" table. It will just be invoked one time when system boot up or reload. The key is chassis_name, the field is "psu_num" and the value is from get_psu_num(). 
- The psu_status and psu_presence will store in "psu_info" table. It will be updated every 3 seconds. The key is psu_name, the field is "presence" and "status", the value is from get_psu_presence() and get_psu_num().
- The daemon query PSU event every 10 seconds via platform API. If any event detects, it should set PSU LED color accordingly and trigger proper syslog.
