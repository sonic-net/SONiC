# SONiC System Health Monitor High Level Design #

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Kebo Liu      | Initial version                   |
 | 0.2 |             |      Junchao Chen  | Check service status without monit|


## 1. Overview of the system health monitor

System health monitor is intended to monitor both critical services/processes and peripheral device status and leverage system log, system status LED to and CLI command output to indicate the system status.

In current SONiC implementation, Monit service can monitor the file system as well as customized script status, system health monitor can rely on Monit service to monitor these items. There are also a set of daemons such as psud, thermaltcld inside PMON to collect the peripheral devices status.

System health monitor needs to monitor the critical service/processes status and borrow the result of Monit service/PMON daemons to summarize the current status and decide the color of the system health LED.

### 1.1 Monitor critical services/processes

#### 1.1.1 Monitor critical services

1. Read FEATURE table in CONFIG_DB, any service whose "STATE" field was configured with "enabled" or "always_enabled" is expected to run in the system
2. Get running services via docker tool (Use python docker library to get running containers)
3. Compare result of #1 and result of #2, any difference will be considered as fault condition

#### 1.1.2 Monitor critical processes

1. Read FEATURE table in CONFIG_DB, any service whose "STATE" field was configured with "enabled" or "always_enabled" is expected to run in the system
2. Get critical processes of each running service by reading file /etc/supervisor/critical_processes (Use `docker inspect <container_name> --format "{{.GraphDriver.Data.MergedDir}}"` to get base director for a container)
3. For each container, use "supervisorctl status" to get its critical process status, any critical process is not in "RUNNING" status will be considered as fault condition.

### 1.2 Services under Monit monitoring

For the Monit, now below programs and file systems are under monitoring:

```
admin@sonic:~$ sudo monit summary -B
Monit 5.20.0 uptime: 22h 56m
 Service Name                     Status                      Type
 sonic                            Running                     System
 rsyslog                          Running                     Process
 root-overlay                     Accessible                  Filesystem
 var-log                          Accessible                  Filesystem
 routeCheck                       Status ok                   Program
 diskCheck                        Status ok                   Program
 container_checker                Status ok                   Program
 vnetRouteCheck                   Status ok                   Program
 container_memory_telemetry       Status ok                   Program
```

By default any service is not in expected status will be considered as fault condition.

### 1.3 Peripheral devices status which could impact the system health status

-  Any fan is missing/broken
-  Fan speed is lower than minimal value
-  PSU power voltage is out of range
-  PSU temperature is higher than threshold
-  PSU is in bad status
-  ASIC temperature is higher than threshold

### 1.4 Customization of monitored critical services and devices

#### 1.4.1 Ignore some of monitored critical services and devices
The list of monitored critical services and devices can be customized by a configuration file, the user can rule out some services or device sensors status from the monitor list. System health monitor will load this configuration file at next run and ignore the services or devices during the routine check.
```json
{
  "services_to_ignore": ["snmpd","snmp_subagent"],
  "devices_to_ignore": ["psu","fan.speed","fan1", "fan2.speed"],
}
```

The filter string is case sensitive. Currently, it support following filters:

- <service_name>: for example, "orchagent", "snmpd", "telemetry"
- asic: ignore all ASIC check
- fan: ignore all fan check
- fan.speed: ignore fan speed check
- <fan_name>: ignore check for a specific fan
- <fan_name>.speed: ignore speed check for a specific fan
- psu: ignore all PSU check
- psu.temperature: ignore temperature check for all PSUs
- psu.voltage: ignore voltage check for all PSUs
- <psu_name>: ignore check for a specific PSU
- <psu_name>.temperature: ignore temperature check for a specific PSU
- <psu_name>.voltage: ignore voltage check for a specific PSU

The default filter is to filter nothing. Unknown filters will be silently ignored. The "services_to_ignore" and "devices_to_ignore" section must be an string array or it will use default filter.

This configuration file will be platform specific and shall be added to the platform folder(/usr/share/sonic/device/{platform_name}/system_health_monitoring_config.json).

#### 1.4.2 Extend the monitoring with adding user specific program to monitor
Monit supports to check program(scripts) exit status, if user wants to monitor something that beyond critical services or some special device not included in the above list, they can provide specific scripts and add them to Monit checking list. Then the result can also be collected by the system health monitor. It requires two steps to add an external checker.

1. Prepare program whose command line output must qualify:

```
<category_name>
<item_name1>:<item_status1>
<item_name2>:<item_status2>
```

2. Add the command line string to configuration:

```json
{
  "external_checkers": ["program_name -option1 value1 -option2 value2"],
}
```

For example, there is a python script "my_external_checker.py", and its output is like:

```
MyCategory
device1:OK
device2:device2 is out of power
```

The configuration shall be:

```json
{
  "external_checkers": ["python my_external_checker.py"],
}
```

### 1.5 System status LED color definition

System status LED is set based on the status of system. The system status is defined as following

 | Status           | Led Color            | Description                                                               |
 |:----------------:|:--------------------:|:-------------------------------------------------------------------------:|
 | booting          | ${led_color.booting} | System up time is less that 5 mins and not all services/devices are ready |
 | normal           | ${led_color.normal}  | All services/devices are in good state                                    |
 | fault            | ${led_color.fault}   | Not all services/devices are in good state                                |


Considering that different vendors platform may have different LED color capability, so LED color for different status also configurable:

```json
{
  "led_color": {
    "fault": "amber",
    "normal": "green",
    "booting": "orange_blink"
  }
}
```

If not configuration is provided, default configuration is used:

```python
DEFAULT_LED_CONFIG = {
	'fault': 'red',
	'normal': 'green',
	'booting': 'red'
}
```

## 2. System health monitor service business logic

System health monitor daemon will run on the host, and periodically (every 60 seconds) check critical services, processes status, output of the command "monit summary", PSU, Fan, and thermal status which is stored in the state DB. If anything is abnormal, system status LED will be set to fault status. When fault condition relieved, system status will be set to normal status.

System health service shall start after database.service and updategraph.service. Monit service has a default 300 seconds start delay, system health service shall not wait for Monit service as Monit service only monitors part of the system. But system health service shall treat system as "Not OK" until Monit service start to work.

Empty FEATURE table will be considered as fault condition.
A service whose critical_processes file cannot be parsed will be considered as fault condition. Empty or absence of critical_processes file is not a fault condition and shall be skipped.
If Monit service is not running or in dead state, the system will be considered in fault condition.
If FAN/PSU/ASIC data is not available, this will be considered as fault condition.
Incomplete data in the DB will also be considered as fault condition, e.g., PSU voltage data is there but threshold data not available.

Monit, thermalctld and psud will raise syslog when fault condition encountered, so system health monitor will only generate some general syslog on these situation to avoid redundant. For example, when fault condition meet, "system health status change to fault" can be print out, "system health status change to normal" when it recovered.


## 3. System health data in redis database

System health service will populate system health data to STATE db. A new table "SYSTEM_HEALTH_INFO" will be created to STATE db.

	; Defines information for a system health
	key                     = SYSTEM_HEALTH_INFO             ; health information for the switch
	; field                 = value
	summary                 = STRING                         ; summary status for the switch
	<item_name>             = STRING                         ; an entry for a service or device

We store items to db only if it is abnormal. Here is an example:

```
admin@sonic:~$ redis-cli -n 6 hgetall SYSTEM_HEALTH_INFO
 1) "fan1"
 2) "fan1 speed is out of range, speed=21.0, range=[24.0,36.0]"
 3) "fan3"
 4) "fan3 speed is out of range, speed=21.0, range=[24.0,36.0]"
 5) "fan5"
 6) "fan5 speed is out of range, speed=22.0, range=[24.0,36.0]"
 7) "fan7"
 8) "fan7 speed is out of range, speed=21.0, range=[24.0,36.0]"
 9) "summary"
10) "Not OK"
```

If the system status is good, the data in redis is like:

```
admin@sonic:~$ redis-cli -n 6 hgetall SYSTEM_HEALTH_INFO
 1) "summary"
 2) "OK"
```

## 4. Platform API and PMON related change to support this new service

To have system status LED can be set by this new service, a system status LED object need to be added to Chassis class. This system status LED object shall be initialized when platform API loaded from host side.

psud need to collect more PSU data to the DB to satisfy the requirement of this new service. more specifically, psud need to collect psu output voltage, temperature and their threshold.

	; Defines information for a psu
	key                               = PSU_INFO|psu_name              ; information for the psu
	; field                           = value
	presence                          = BOOLEAN                        ; presence of the psu
	model                             = STRING                         ; model name of the psu
	serial                            = STRING                         ; serial number of the psu
	status                            = BOOLEAN                        ; status of the psu
	change_event                      = STRING                         ; change event of the psu
	fan                               = STRING                         ; fan_name of the psu
	led_status                        = STRING                         ; led status of the psu
	temp                              = INT                            ; temperature of the PSU
	temp_th                           = INT                            ; temperature threshold
	voltage                           = INT                            ; output voltage of the PSU
	voltage_max_th                    = INT                            ; max threshold of the output voltage
	voltage_min_th                    = INT                            ; min threshold of the output voltage
	power_overload                    = "true" / "false"               ; whether the PSU's power exceeds the threshold
	power_warning_suppress_threshold  = 1*4.3DIGIT                     ; The power warning threshold
	power_critical_threshold          = 1*4.3DIGIT                     ; The power critical threshold

## 5. System health monitor CLI

Add a new "show system-health" command line to the system

	admin@sonic# show ?
	Usage: show [OPTIONS] COMMAND [ARGS]...

	  SONiC command line - 'show' command

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  ...
	  startupconfiguration  Show startup configuration information
	  subinterfaces         Show details of the sub port interfaces
	  system-memory         Show memory information
      system-health         Show system health status
      ...

"show system-health" CLI has three sub command, "summary" and "detail" and "monitor-list". With command "summary" will give brief output of system health status while "detail" will be more verbose.
"monitor-list" command will list all the services and devices under monitoring.

    admin@sonic# show system-health ?
	Usage: show system-health [OPTIONS] COMMAND...

	  SONiC command line - 'show system-health' command

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  summary          Show system-health summary information
	  detail           Show system-health detail information
      monitor-list     Show system-health monitored services and devices name list

output is like below:

when everything is OK

    admin@sonic# show system-health summary
    System status LED  green
	Services           OK
	Hardware           OK

When something is wrong

    admin@sonic# show system-health summary
    System status LED  amber
	Services           Fault
        orchagent is not running
	Hardware           Fault
        PSU 1 temp 85C and threshold is 70C
        PSU 1 power (66.32w) exceeds the threshold (60.00w)
        FAN 2 is broken

for the "detail" sub command output, it will give out all the services and devices status which is under monitoring, and also the ignored service/device list will also be displayed.

"monitor-list" will give a name list of services and devices exclude the ones in the ignore list.

When the CLI been called, it will directly analyze the "monit summary" output and the state DB entries to present a summary about the system health status. The status analyze logic of the CLI shall be aligned/shared with the logic in the system health service.

Fault condition and CLI output string table
 | Fault condition         |CLI output     |
 |:-----------------------:|:-------------:|
 | critical service failure|[service name] is [service status]|
 | Any fan is missing/broken   |[FAN name] is missing/broken|
 | Fan speed is below minimal range|[FAN name] speed is lower than expected|
 | PSU power voltage is out of range|[PSU name] voltage is out of range|
 | PSU power exceeds threshold|[PSU name] power exceeds threshold|
 | PSU temp is too hot|[PSU name] is overheated|
 | PSU is in bad status|[PSU name] is broken|
 | ASIC temperature is too hot|[ASIC name] is overheated|
 | monit service is not running| monit is not running|
 | PSU data is not available in the DB|PSU data is not available|
 | FAN data is not available in the DB|FAN data is not available|
 | ASIC data is not available in the DB|ASIC data is not available|

## 6. System health monitor test plan

1. If some critical service missed, check the CLI output, the LED color and error shall be as expected.
2. Simulate PSU/FAN/ASIC and related sensor failure via mock sysfs and check the CLI output, the LED color and error shall be as expected.
3. Change the monitor service/device list then check whether the system health monitor service works as expected; also check whether the result of "show system-health monitor-list" aligned.
