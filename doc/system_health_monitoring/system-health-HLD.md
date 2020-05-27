# SONiC System Health Monitor High Level Design #

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Kebo Liu      | Initial version                   |



## 1. Overview of the system health monitor

System health monitor is intend to monitor both of critical services and peripheral device status and leverage system log, system health LED to and CLI command output to indicate the status.

In current SONiC implementation, already have Monit which is monitoring the critical services status and also have a set of daemons(psud, thermaltcld) inside PMON collecting the peripheral devices status.

System health will not monitor the critical services or devices directly, it will reuse the result of Monit and PMON daemons to summary the current status and decide the color of the system health status.

### 1.1 Services under Monit monitoring

For the Monit, now below services and file system is under monitoring:

	admin@sonic# monit summary -B
	Monit 5.20.0 uptime: 1h 6m
	 Service Name                     Status                      Type
	 sonic                            Running                     System
	 rsyslog                          Running                     Process
	 telemetry                        Running                     Process
	 dialout_client                   Running                     Process
	 syncd                            Running                     Process
	 orchagent                        Running                     Process
	 portsyncd                        Running                     Process
	 neighsyncd                       Running                     Process
	 vrfmgrd                          Running                     Process
	 vlanmgrd                         Running                     Process
	 intfmgrd                         Running                     Process
	 portmgrd                         Running                     Process
	 buffermgrd                       Running                     Process
	 nbrmgrd                          Running                     Process
	 vxlanmgrd                        Running                     Process
	 snmpd                            Running                     Process
	 snmp_subagent                    Running                     Process
	 sflowmgrd                        Running                     Process
	 lldpd_monitor                    Running                     Process
	 lldp_syncd                       Running                     Process
	 lldpmgrd                         Running                     Process
	 redis_server                     Running                     Process
	 zebra                            Running                     Process
	 fpmsyncd                         Running                     Process
	 bgpd                             Running                     Process
	 staticd                          Running                     Process
	 bgpcfgd                          Running                     Process
	 root-overlay                     Accessible                  Filesystem
	 var-log                          Accessible                  Filesystem


By default any above services or file systems is not in good status will be considered as fault condition.

### 1.2 Peripheral devices status which could impact the system health status

-  Any fan is missing/broken
-  Fan speed is below minimal range
-  PSU power voltage is out of range
-  PSU temperature is too hot
-  PSU is in bad status
-  ASIC temperature is too hot

### 1.3 Customization of monitored critical services and devices

#### 1.3.1 Ignore some of monitored critical services and devices
The list of monitored critical services and devices can be customized by a configuration file, the user can rule out some services or device sensors status from the monitor list. System health monitor will load this configuration file at the start and ignore the services or devices during the routine check.

	{
	    services_to_ignore: {
		snmpd,
		snmp_subagent
	    },
	    devices_to_ignore: {
		psu
	    }

	}

This configuration file will be platform specific and shall be added to the platform folder(/usr/share/sonic/device/{platform_name}/system_health_monitoring_config.json).

#### 1.3.2 Extend the monitoring with adding user specific program to Monit
Monit support to check program(scripts) exit status, if user want to monitor something that beyond critical serives or some device not included in the above list, they can provide a specific scripts and add it to Monit check list, then the result can also be collected by the system health monitor.  

### 1.4 system status LED color definition

default system status LED color definition is like 

 | Color            |     Status    |       Description       |
 |:----------------:|:-------------:|:-----------------------:|
 | Off              |  off          |   no power              |
 | Blinking amber   |  boot up      |   switch is booting up  |
 | Red              |  fault        |   in fault status       |
 | Green            |  Normal       |   in normal status      |

Considering that different vendors platform may have different LED color capability, so LED color for different status also configurable:

	{
	    status_led_color: {
		fault: 'amber',
		normal: 'green'
	    }
	}


## 2. System health monitor service business logic

System health monitor daemon will running on the host, periodically(every 60s) check the "monit summary" command output and PSU, fan, thermal status which stored in the state DB, if anything wrong with the services monitored by monit or peripheral devices, system status LED will be set to fault status. When fault condition relieved, system status will be set to normal status. 

Before the switch boot up finish, the system health monitoring service shall be able to know the switch is in boot up status(see open question 1).

If monit service is not avalaible, will consider it as fault condition.
FAN/PSU/ASIC data not available will also considered as fault conditon.
Incomplete data in the DB will also be considered as fault condition, e.g., voltage data is there but threshold data not available.

Monit, thermalctld and psud will raise syslog when fault condition encounterd, so system health monitor will only generate some general syslog on these situation to avoid redundant. For example, when fault condition meet, "system health status change to fault" can be print out, "system health status change to normal" when it recovered.

this service will be started after system boot up(after rc.local).

## 3. Platform API and PMON related change to support this new service

To have system LED can be set by this new service, a system LED object need to be added to Chassis class. This system LED object shall be initialized when platform API loaded from host side.

psud need to collect more PSU data to the DB to satisfy the requirement of this new service. more specifically, psud need to collect psu output voltage, temperature and their threshold.

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
	temp                    = INT                            ; temperature of the PSU
	temp_th                 = INT                            ; temperature threshold
	voltage                 = INT                            ; output voltage of the PSU
	voltage_max_th          = INT                            ; max threshold of the output voltage
	voltage_min_th          = INT                            ; min threshold of the output voltage

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

"show system-health" CLI has three sub command, "summary" and "detail" and "monitor-list". With command "summary" will give brief outpt of system health status while "detail" will be more verbose.
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
        FAN 2 is broken

for the "detail" sub command output, it will give out all the services and devices status which is under monitoring, and also the ignored service/device list will also be displayed.

"moniter-list" will give a name list of services and devices exclude the ones in the ignore list.

When the CLI been called, it will directly analyze the "monit summary" output and the state DB entries to present a summary about the system health status. The status analyze logic of the CLI shall be aligned/shared with the logic in the system health service.

Fault condition and CLI output string table
 | Fault condition         |CLI output     |
 |:-----------------------:|:-------------:|
 | critical service failure|[service name] is [service status]|
 | Any fan is missing/broken   |[FAN name] is missing/broken|
 | Fan speed is below minimal range|[FAN name] speed is lower than expected|
 | PSU power voltage is out of range|[PSU name] voltage is out of range|
 | PSU temp is too hot|[PSU name] is overheated|
 | PSU is in bad status|[PSU name] is broken|
 | ASIC temperature is too hot|[ASIC name] is overheated|
 | monit service is not running| monit is not running|
 | PSU data is not available in the DB|PSU data is not available|
 | FAN data is not available in the DB|FAN data is not available|
 | ASIC data is not available in the DB|ASIC data is not available|

See open question 2 for adding configuration CLIs. 

## 6. System health monitor test plan

1. Kill some critical service and check the CLI output, the LED color and error shall be as expected.
2. Simulate PSU/FAN and related sensor failure via mock sysfs and check the CLI output, the LED color and error shall be as expected.
3. Change the monitor service/device list and restart the system health monitor service, then check whether the system health monitor service works as expected; also check whether the result of "show system-health monitor-list" aligned. 

## 7. Open Questions
1. How to determine the SONiC system is in boot up stage ?
2. Is it necessary to add a CLI to manipulate the configuration file? Like add/remove service/device from ignore list? 

