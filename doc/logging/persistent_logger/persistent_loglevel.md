# Persistent logger HLD

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [Persistent logger HLD](#persistent-logger-hld)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.1](#rev-01)
- [Table of Contents](#table-of-contents)
- [List of Tables](#list-of-tables)
- [List of Figures](#list-of-figures)
- [Revision](#revision)
- [Scope](#scope)
- [Motivation](#motivation)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [1 Background](#1-background)
  - [1.1 "swssloglevel" usage](#11-"swssloglevel"-usage)
  - [1.2 LOGLEVEL DB schema](#12-loglevel-db-schema)
- [2 Requirements Overview](#2-requirements-overview)
- [3 Persistent log level design](#3-persistent-log-level-design)
  - [3.1 High-level design](#31-high-level-design)
  - [3.2 Persistent logger flow](#32-persistent-logger-flow)
    - [3.2.1 Return to default log level](#321-return-to-default-log-level)
- [4 Flows](#4-flows)
  - [4.1 System init flow](#41-system-init-flow)
  - [4.2 "config reload" flow](#42-"config-reload"-flow)
  - [4.3 "config save" flow](#43-"config-save"-flow)
- [5 Warm Reboot Support](#5-warm-reboot-support)
  - [5.1 Make the log level persistent to warm-reboot only by command](#51-make-the-log-level-persistent-to-warm-reboot-only-by-command)
- [6 Fast Boot Support](#6-fast-boot-support)
- [7 Testing](#7-Testing)
  - [7.1 Unit Testing](#71-unit-testing)
  - [7.2 Manual Testing](#72-manual-testing)
- [8 Open Questions](#8-open-questions)
  - [8.1 Log level persistency in warm-reboot](#81-log-level-persistency-in-warm-reboot)

# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)


# List of Figures
* [log-level save command](#32-persistent-logger-flow)
* [persistent logger flow](#321-return-to-default-log-level)



# Revision
| Rev | Date     | Author          | Change Description                 |
|:---:|:--------:|:---------------:|------------------------------------|
| 0.1 | 07/20/22 | Eden Grisaro    | Initial version                    |

# Scope
This document provides high level design for SWSS Logger - log level persistent for SWSS, Syncd, and SAI components.

# Motivation
Log level verbosity is part of the configuration of the OS. Today, the log level is not persistent and gets a default value after reboot. It is required to add the ability to make the loglevel persistent.

# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| SONiC         | Software for open networking in the cloud | 
| SAI           | Switch Abstraction Interface              |


# 1 Background
Today, the user can configure the log level verbosity to each component in SWSS, Syncd, and SAI. In order to configure the log level in runtime, the user uses the **"swssloglevel" script**. The script updates the **LOGLEVEL DB** with the new verbosity. After a cold/fast reboot, the LOGLEVEL DB flushes, and the log level value of all components returns to default. For warm reboot, the log level will remain (as it is in today's implementation).

## 1.1 "swssloglevel" usage

The "swssloglevel" options:

```
admin@sonic:~$ swssloglevel -h
Usage: swssloglevel [OPTIONS]
SONiC logging severity level setting.

Options:
	 -h	print this message
	 -l	loglevel value
	 -c	component name in DB for which loglevel is applied (provided with -l)
	 -a	apply loglevel to all components (provided with -l)
	 -s	apply loglevel for SAI api component (equivalent to adding prefix "SAI_API_" to component)
	 -p	print components registered in DB for which setting can be applied

Examples:
	swssloglevel -l NOTICE -c orchagent # set orchagent severity level to NOTICE
	swssloglevel -l SAI_LOG_LEVEL_ERROR -s -c SWITCH # set SAI_API_SWITCH severity to ERROR
	swssloglevel -l SAI_LOG_LEVEL_DEBUG -s -a # set all SAI_API_* severity to DEBUG

```

## 1.2 LOGLEVEL DB schema

The LOGLEVEL DB is database #3. It contains a table for each component.
Here is an example of the orchagent component table:

```
admin@sonic:~$ redis-cli -n 3 HGETALL "orchagent:orchagent"

1) “LOGLEVEL”

2) “INFO”

3) “LOGOUTPUT”

4) “SYSLOG”
```


# 2 Requirements Overview

The persistent Logger should meet the following high-level functional requirement:
- The user will be able to save the configuration of the loglevel and make it persistent after reboot.

# 3 Persistent log level design
## 3.1 High-level design

Two different design approaches were considered for making the loglevel persistent to reboot:
1. Move the LOGLEVEL DB content into the Config DB. Since the Config DB is already persistent, the log level will also be persistent to reboot. The log level will be saved when using the "config save" CLI command.
2. Keep using the existing LOGLEVEL DB and make it persistent by adding loglevel_db.json file that will keep LOGLEVEL DB content with dedicated CLI command to save only LOG configuration.

There was a concern that the first approach would impact the boot time. In addition we wanted to keep the flexibility for the user to save the log level in a separate flow (and not to save the log level following regular config save), it was decided to go with the second approach.

### Making LOGLEVEL DB persistent by adding "loglevel_db.json" file

 - We will add a new "log-level save" command to allow the user to save the log level.

```
admin@sonic:~$ log-level save
```

 
 - Similar to the config_db.json, we will add a new loglevel_db.json. The JSON file will be added to etc/sonic/loglevel_db.json.

```json
{
  "LOGGER": {
    "orchagent:orchagent": {
      "LOGLEVEL": "INFO",
      "LOGOUTPUT": "SYSLOG"
    }
  }
}
```

- On "swssloglevel": We will set the log level to the LOGLEVEL DB, This is the behavior as we have today, and it remains as it is.
- On "log-level save": We will copy the LOGLEVEL DB content into the loglevel_db.json (overriding existing file, if exists).
- On init: we will load the loglevel_db.json file into the LOGLEVEL DB.

![log-level save command](/doc/logging/persistent_logger/log-level_save_command.drawio.png)


## 3.2 Persistent logger flow

- Each component has a singleton Logger object with a log level property and listener thread.
- On init:
  - The loglevel_db.json file is loaded into the LOGLEVEL DB during the init of database docker.
  - The loglevel property is set accordingly to the loglevel value on the LOGLEVEL DB.
- When a component writes a log message, the Logger writes the message only if the loglevel of the message is above the current loglevel property.
- When the user wants to set a new log level to a component, he uses the "swssloglevel" CLI command. The "swssloglevel" script sets the new verbosity to the LOGLEVEL DB (database #3).
- The LOGLEVEL DB change triggers an event, which is caught by the listener thread.
- The listener thread changes the loglevel property of the Logger.
- The user can use the "log-level save" command to save the current loglevel and make it persistent. It will copy the LOGLEVEL DB content into the loglevel_db.json.
In addition to the log level, the LOGLEVEL DB contains the log output file. After "log-level save" the log output will be persistent to reboot too.

### 3.2.1 Return to default log level

  To return to the default log level, the user will delete the loglevel_db.json and reboot the switch.





![persistent logger flow](/doc/logging/persistent_logger/persistent_logger.png)







# 4 Flows

## 4.1 System init flow

When the system startup and the Database container initialize, we will load the loglevel_db.json into the LOGLEVEL DB (similar to the config_db.json). If the loglevel.json file is not exist, the system will generate a new loglevel_db.json automatically only after the user run "log-level save".
The Link to the place of loading loglevel_db.json into LOGLEVEL DB will be:  https://github.com/Azure/sonic-buildimage/blob/master/files/build_templates/docker_image_ctl.j2#L222

  - There is a concern about the log level of messages written before the database container is initialized (if it exists). From my understanding, the RSYSLOG-CONFIG is up only after the DATABASE container, so there won't be logs before the loglevel_db.json loads into the LOGLEVEL DB. In case there are messages before the loading, the messages will be in the default log level.

## 4.2 "config reload" flow

  When the user runs "config reload", not only the config_db.json will load into the CONFIG DB, but also the loglevel_db.json will load into the LOGLEVEL DB.

  - We will **not** create similar CLI command to "config reload". The "config reload" command is necessary for features that can only configure from the config_db.json; this ability is unnecessary in the persistent loglevel feature.

  Link to the place in the code that loads the config_db.json into the CONFIG DB: https://github.com/Azure/sonic-utilities/blob/ca728b8961812a28e3542b206417755f4fe2ba89/config/main.py#L1401

## 4.3 "config save" flow

  When the user runs "config save", it will not affect the loglevel state.
   - If the user wants to save its log level configuration, he will use the dedicated CLI command "log-level save".

# 5 Warm Reboot Support
  
  With current implementation, we don't flush the LOGLEVEL DB before warm-reboot, which means that if the user configures some loglevel (for example, debug), after warm-reboot, the system startup with the same configurable loglevel (debug).
  Because we want to make the log level persistent to reboot only by the "log-level save" CLI command we will add the LOGLEVEL DB to the list of the dbies we flush before warm-reboot.
  During boot time, in the startup, the loglevel_db.json will load on the LOGLEVEL DB.

# 6 Fast Boot Support

  In the fast-boot, the database content is deleted. To make the log level persistent to fast-boot, we need to load the loglevel_db.json into the LOGLEVEL DB in the startup. Since the startup is from another partition, we need to migrate the loglevel_db.json similarly to the migrate in the config_db.json.

# 7 Testing
## 7.1 Unit Testing

  1. Verify that "config reload" loading the loglevel_db.json into LOGLEVEL DB:
    1.1 Change log level for some component Notice to Info.
    1.2 Run "log-level save".
    1.3 Change the log level again to the same component from Info to Warnning.
    1.4 Run "config reload".
    1.5 Verify the log level is "Info".

## 7.2 Manual Testing 

  1. Verify log level is persistent to cold/fast/warm reboot after user run "log-level save":
    1.1 Change log level for some component from Notice to Info.
    1.2 Run "log-level save".
    1.3 Verify the loglevel.json file was created.
    1.3 Reboot.
    1.4 Verify the log level is "Info".
  2. Verify log level is not persistent to cold/fast/warm reboot if the user didn't run "log-level save": 
    2.1 Change log level for some component Notice to Info.
    2.2 Reboot.
    2.3 Verify the log level is "Notice".
  3. Verify loglevel returns to default after removing the "loglevel_db.json" file and reboot:
    3.1 Change log level for some component Notice to Info.
    3.2 Run "log-level save".
    3.3 Delete loglevel_db.json file.
    3.3 Reboot.
    3.4 Verify the log level is "Notice".

  
# 8 Open Questions

## 8.1 Log level persistency in warm-reboot
  
 - Do we want to keep that the loglevel is persistent to warm-reboot automatically as it is today?


