# Clock Managment Design #

## Table of Content 


* 1. [Table of Content](#TableofContent)
	* 1.1. [Revision](#Revision)
	* 1.2. [Scope](#Scope)
	* 1.3. [Definitions/Abbreviations](#DefinitionsAbbreviations)
	* 1.4. [Overview](#Overview)
	* 1.5. [Requirements](#Requirements)
		* 1.5.1. [Functional requirements](#FunctionalRequirements)
		* 1.5.2. [Configuration and Management Requirements](#ConfigurationManagementRequirements) 
* 2. [Design](#Design)
	* 2.1. [High-Level Design](#High-LevelDesign)
* 3. [Configuration and management](#Configurationandmanagement)
	* 3.1. [ConfigDB Tables](#ConfigDBTables)
	* 3.2. [CLI/YANG model](#CLIYANGmodel)
		* 3.2.1. [Yang model](#Yangmodel)
		* 3.2.2. [CLI](#Climodel)
* 4. [Test Plan](#TestPlan)
		* 4.1. [Unit Test cases](#UnitTestcases)


### 1.1 <a name='Revision'></a>Revision

|  Rev  |  Date   |      Author      | Change Description |
| :---: | :-----: | :--------------: | :----------------: |
|  0.1  | 01/2023 |   Meir Renford   | High level Design  |

###  1.2. <a name='Scope'></a>Scope

This document will address the high level design for clock commands:
1.	Set/show date-time command
2.	Set/show timezone command


### 1.3 <a name='DefinitionsAbbreviations'></a>Definitions/Abbreviations 

N/A

### 1.4 Overview 

The clock commands allow to set and review the current time parameters of the system - including: time, date and timezone. 

### 1.5 Requirements
####  1.5.1. <a name='FunctionalRequirements'></a>Functional requirements

1. Any time/date configuration will change accordingly the system time. 

####  1.5.2. <a name='ConfigurationManagementRequirements'></a>Configuration and Management Requirements
The requirements from the module are: 
1.	Set and show the system time and date.
2.	Set and show the system timezone.


##  2 <a name='Design'></a>Design

###  2.1 <a name='High-LevelDesign'></a>High-Level Design

The design of this feature is based on Linux command of <b>timedatectl</b>.<BR>
(man page for timedatectl: https://man7.org/linux/man-pages/man1/timedatectl.1.html)

All set operations are based on this command, executing directly in linux upon user CLI execution.
The time/date/timezone are configured directly to Linux, and is persistent upon any reboot.

System state of time/date/timezone will appear in 1 line as an output of existing "show clock" command.

hostcfgd will be the daemon in charge of this configuration management.

<u>CLI Commands desin:</u><br>

	Set operations will be divided into 2 different commands:

	1. config clock timezone <timezone> (to set timezone command)
		* will get single input as a string, and validate it is valid as part of ("timedatectl list-timezones" command).
		Validation will be done either by YANG model, or (if not possible) by issueing relevant error to log.
		* Value will be stored in db for future upgrade operations.
		Value is persistent upon reboot.
		* Linux timedatectl with set-timezone flag will be called.
		e.g. timedatectl set-timezone "Asia/Kolkata"
		* <b>In case NTP is enabled -> timezone configuration is allowed and overrides the current time.</b>
		* Date & timezone setting will be reflected of all the services/dockers in the system.


	2. config clock date <YYYY-MM-DD> <HH:MM:SS> (to set time and date)
		* Command will recieve single string with date-time format <YYYY-MM-DD> <HH:MM:SS>
		* Command does not need to be stored in DB.
		* Linux timedatectl with set-time flag will be called.
		e.g. timedatectl set-time "2012-10-30 18:17:16"
		* <b>In case NTP is enabled -> time/date set is NOT allowed and being blocked</b>

	Additional show command will be added to display all valid timezones:

	3. show clock timezones

		* Will display list of all valid timezones to be configured.
		* based on "timedatectl list-timezones" linux command.


<u>General notes:</u><br>

	* Both set commands will be written directly to Linux (via imedatectl command), and will be activated immediately.

	* In case of any set command (time/date/timezone) a relevant message will be print to syslog.

	* In case of any set command (time/date/timezone) - rsyslog service should be restarted to reflect the time change.

	* Upgrades - timezone configuration is part of DEVICE_METADATA, hence - configuration upgrade will be taken care of as any other sonic configuration.


##  3 <a name='Configurationandmanagement'></a>Configuration and management

###  3.1 <a name='ConfigDBTables'></a>ConfigDB Tables

Only timezone configuration will be saved.
Additional field will be added to DEVICE_METADATA table

```
DEVICE_METADATA :{
    "timezone": {{string}}
}
```

default value: "Etc/UTC"


###  3.2 <a name='CLIYANGmodel'></a>CLI/YANG model

####  3.2.1. <a name='Yangmodel'></a>Yang model


Adding to existing Yang model of device_metadata (https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-device_metadata.yang)

```
    container sonic-device_metadata {

        container DEVICE_METADATA {

            description "DEVICE_METADATA part of config_db.json";

            container localhost{
			...
				leaf timezone {
					type string;
					description "System time-zone setting";
				}
```

####  3.2.2. <a name='Climodel'></a>CLI

##### Show CLI

```
root@host:~$ show clock 
Sun 15 Jan 2023 06:12:08 PM IST

```

```
root@host:~$ show clock timezones
Africa/Abidjan
Africa/Accra
Africa/Addis_Ababa
Africa/Algiers
Africa/Asmara
...

```

##### Config CLI

```
root@host:~$ config clock timezone "<timezone>"

```

```
root@host:~$ config clock date <YYYY-MM-DD> <HH:MM:SS>

```


##  4 <a name='TestPlan'></a>Test Plan

###  4.1 <a name='UnitTestcases'></a>Unit Test cases

1. Good flows:<br>
	a. set timezone - <br>
	output of the set command is empty, and expect to see the new timezone in show command output, and the time is correlated with this timezone.<br><br>

	b. set date & time - <br>
	- output of the set command is empty, and expect to see the new date & time in show command output.<br><br>

	c. check reboot - <br>
	rebooting without config save restores configuration (timezone) to the saved one.<br><br>

	d. check docker restart - <br>
	expect to see the time remains as system time.<br><br>

	e. config load / reload <> - <br>
	expect to see timezone changes upon new configuration.<br><br>

	f. reboot without config save - <br>
	expect rebooting without config save restores configuration (timezone) to the saved one.<br><br>

	g. upgrade with manually timedatectl before upgrade - <br>
	Expect to have configuration timezone (if configuration exist) apply and change the timedatectl.<br><br>
	

2. Bad flows:<br>
	a. set invalid timezone - <br>
	expect for error message for invalid timezone, and timezone shouldn’t change (remains the same in show command output).<br><br>

	b. set empty string - <br>
	expect for error message for empty / incomplete command. Nothing should be changed after it.<br><br>

	c. set invalide date/time format - <br>
	expect for error message for the invalid parameter.<br><br>

3. NTP interop<br>
	a. Change time/date, followed by changing NTP - and see time changed.<br>
	b. try to change time/date in case NTP is enabled -> and expect getting a failure.<br>
	c. Change timezone in case NTP is enabled, and expect to succeed and change relevant time.<br>

4. Rsyslog:<br>
	a. In case of any set command (time/date/timezone) - verify rsyslog service should be restarted to reflect the time change.

* Functional tests covering flows above will be part of sonic-mgmt tests suite.
