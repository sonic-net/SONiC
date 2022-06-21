# Persistent logger HLD

# High Level Design Document

#### Rev 0.1

# todo update
# Table of Contents
- [What Just Happened in SONiC HLD](#what-just-happened-in-sonic-hld)
- [High Level Design Document](#high-level-design-document)
      - [Rev 0.3](#rev-03)
- [3 Modules design](#3-modules-design)
  - [3.13 WJH daemon](#313-wjh-daemon)
    - [3.13.1 Push vs Pull](#3131-push-vs-pull)

# todo update
# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)
* [Table 2: Raw Channel Data](#raw-channel-1)
* [Table 3: Aggregated Channel Data](#aggregated-channel)

# todo update
# List of Figures
* [WJH in SONiC](#33-wjh-in-sonic-overview)
* [Init flow](#41-wjhd-init-flow)
* [Channel create and set flow](#42-wjhd-channel-create-and-set-flow)


# Revision
| Rev | Date     | Author          | Change Description                 |
|:---:|:--------:|:---------------:|------------------------------------|
| 0.1 | 06/21/22 | Eden Grisaro    | Initial version                    |

# Scope
This document provides an overview of the implementation of making the SWSS Logger persistent for SWSS, Syncd, and SAI components.

# Motivation
Log level verbosity is part of the configuration of the OS. Today, the log level is not persistent and gets a default value after reboot. It is required to add the ability to make the loglevel persistent.

# todo update
# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| SONiC         | Software for open networking in the cloud | 
| SAI           | Switch Abstraction Interface              |


# 1 Background
Today, the user can configure the log level verbosity to each component in SWSS, Syncd, and SAI. In order to configure the log level in runtime, the user uses the "swssloglevel" script. The script updates the LOGLEVEL DB with the new verbosity. After reboot, the LOGLEVEL DB flushes, and the log level value of all components returns to default.

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
admin@sonic:~$ redis-cli -n 3 HGETALL ‘orchagent:orchagent’

1) “LOGLEVEL”

2) “INFO”

3) “LOGOUTPUT”

4) “SYSLOG”
```


# 2 Requirements Overview

The persistent Logger should meet the following high-level functional requirement:
- The user will be able to save the configuration of the loglevel and make it persistent after reboot. The default will be no persistent.

# 3 Persistent log level design
## 3.1 High-level design

In the begining we consider two diffrent design aproaches for making the loglevel persistent to reboot:
1. Keep using the existing LOGLEVEL DB and make it persistent by adding loglevel_db.json file. 
2. Move the LOGLEVEL DB content into the Config DB. Since the Config DB is already persistent, the log level will also be persistent to reboot. The log level will be saved when using the "config save" CLI command.

We discarded this second approach to allow users to save the log level with deticated command and not exesiting command that will save other configuration too.

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

- On "swssloglevel": We will set the log level to the LOGLEVEL DB (This is the behavior we have today and it redmain as it is).
- On "log-level save": We will copy the LOGLEVEL DB content into the loglevel_db.json.
- On startup: we will load the loglevel_db.json file into the LOGLEVEL DB.


## 3.3 Persistent logger flow

- Each component has a singleton Logger object with a log level property and listener thread.
- On startup:
  - The loglevel_db.json file is loaded into the LOGLEVEL DB during the init of database docker.
  - The loglevel property is set accordingly to the loglevel value on the LOGLEVEL DB.
- When a component writes a log message, the Logger writes the message only if the loglevel of the message is above the current loglevel property.
- When the user wants to set a new log level to a component, he uses the "swssloglevel" CLI command. The "swssloglevel" script sets the new verbosity to the LOGLEVEL DB (database #3).
- The LOGLEVEL DB change triggers an event, which is caught by the listener thread.
- The listener thread changes the loglevel property of the Logger.
- The user can use the "log-level save" command to save the current loglevel and make it persistent. It will copy the LOGLEVEL DB content into the loglevel_db.json.
In addition to the log level, the LOGLEVEL DB contains the log output file. After "log-level save" the log output will be persistent to reboot too.


![persistent logger flow](/doc/logging/persistent_logger/persistent_logger.png)




#todo add init flow

# 4 Flows

## 4.1 Logger init flow todo complete

##todo comlete dast, warm, cold reboot and config reload 

# 5 Warm Boot Support

# todo check who it impact today

## 5.1 System level

## 5.2 Service level

# 6 Fast Boot Support

consider return to default before

# 7 Open Questions