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
- [6 Fast Boot Support](#6-fast-boot-support)
- [7 Testing](#7-Testing)
  - [7.1 Unit Testing](#71-unit-testing)
  - [7.2 Manual Testing](#72-manual-testing)
- [8 Open issues](#8-open-issues)
  - [8.1 Allow changing the default log level in first boot](#81-allow-changing-the-default-log-level-in-first-boot)
  - [8.2 Support ZTP configuration](#82-support-ztp-configuration)
# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)


# List of Figures
* [log-level save command](#32-persistent-logger-flow)
* [persistent logger flow](#321-return-to-default-log-level)



# Revision
| Rev | Date     | Author          | Change Description                |
|:---:|:--------:|:---------------:|-----------------------------------|
| 0.1 | 07/20/22 | Eden Grisaro    | Initial version                   |

# Scope
This document provides high level design for SWSS Logger - log level persistent for SWSS, Syncd, and SAI components.

# Motivation
Log level verbosity is part of the configuration of the OS. Today, the log level is not persistent and gets a default value after reboot. It is required to add the ability to make the loglevel persistent.

# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| SONiC         | Software for open networking in the cloud | 
| SAI           | Switch Abstraction Interface              |
| CONFIG DB	    | Configuration Database                    |


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
- Not impact warm/fast reboot when the user uses the default configuration.

# 3 Persistent log level design
## 3.1 High-level design

To make the loglevel persistent to reboot, we will move the LOGLEVEL DB content into the Config DB. Since the Config DB is already persistent, the log level will also be persistent to reboot. The log level will be saved using the "config save" CLI command.

### 3.1.1 CONFIG DB schema

 - A new "LOGGER" table will be added to the CONFIG DB:

```json
{
  "LOGGER": {
    "orchagent": {
      "LOGLEVEL": "INFO",
      "LOGOUTPUT": "SYSLOG"
    }
  }
}
```

 There will be a minor change in the table keys(instead of "{componentName}:{componentName}" the key will be just the "{componentName}").

### 3.1.2 Delete LOGLEVEL DB
???
 - We will remove LOGLEVEL DB?
 - CHANGE SCHEMA.H NO DB 3

### 3.1.3 Add "config loglevel" CLI command to replace the "swssloglevel" script

In the current implementation the "swssloglevel" script sets the log level in the LOGLEVEL DB. We will replace the script with a CLI command with the same functionality, execet that the log level will be saved in the CONFIG DB.

To allow the user to set the default log level value for all the components, we will add a -d flag to the "config loglevel" command.

```
admin@sonic:~$ config loglevel -h

Usage: config loglevel [OPTIONS]
SONiC logging severity level setting.

Options:
	 -h	print this message
	 -l	loglevel value
	 -c	component name in DB for which loglevel is applied (provided with -l)
	 -a	apply loglevel to all components (provided with -l)
	 -s	apply loglevel for SAI api component (equivalent to adding prefix "SAI_API_" to component)
	 -p	print components registered in DB for which setting can be applied
   -d return all components to default loglevel

Examples:
	config loglevel -l NOTICE -c orchagent # set orchagent severity level to NOTICE
	config loglevel -l SAI_LOG_LEVEL_ERROR -s -c SWITCH # set SAI_API_SWITCH severity to ERROR
	config loglevel -l SAI_LOG_LEVEL_DEBUG -s -a # set all SAI_API_* severity to DEBUG
  config loglevel -d #return all components to default loglevel
```

### 3.1.4 Make the log level persistent using the "config save" CLI command

The content of the CONFIG DB will load into the config_db.json. This is the behavior we have today, and it remains as it is. If the user configures loglevel for some component and runs "config save" the loglevel will be persistent.

### 3.1.5 Listener thread tables

In the current implementation, each component has a listener thread that registers to the LOGLEVEL DB table. Each change in the LOGLEVEL DB table is caught by the thread and trigger handler that change the component's Logger configuration. We will keep the same behavior on the CONFIG DB.

## 3.2 Persistent logger flow

- Each component has a singleton Logger object with a log level property and listener thread.
- When a component writes a log message, the Logger writes the message only if the loglevel of the message is above the current loglevel property.
- When the user wants to set a new log level to a component, he uses the "config loglevel" CLI command. The "config loglevel" CLI command sets the new verbosity to the CONFIG DB (database #4).
- The CONFIG DB change triggers an event, which is caught by the listener thread.
- The listener thread changes the loglevel property of the Logger.
- The user can use the "config save" command to save the current loglevel and make it persistent. It will copy the CONFIG DB content into the config_db.json.

In addition to the log level, the CONFIG DB contains the log output file. After "config save" the log output will be persistent to reboot too.







![persistent logger flow](/doc/logging/persistent_logger/persistent_loglevel.png)







# 4 Flows???????

## 4.1 System init flow

When the system startup and the Database container initialize, the config_db.json loads into the CONFIG DB.
 
  - There is a concern about the log level of messages written before the database container is initialized (if it exists). From my understanding, the RSYSLOG-CONFIG is up only after the DATABASE container, so there won't be logs before the loglevel_db.json loads into the LOGLEVEL DB. In case there are messages before the loading, the messages will be in the default log level.


# 5 Cold and Fast Reboot Support
  
  The current implementation support cold and fast reboot. Sine in the cold and fast reboot, the CONFIG DB content is deleted the user need to run "config save" to make the log level persistent to cold and fast reboot.

# 6 Warm Reboot Support

  With current implementation, we don't flush the CONFIG DB before warm-reboot, which means that if the user configures some loglevel (for example, debug), after warm-reboot, the system startup with the same configurable loglevel (debug).

  ?????
  Because we want to make the log level persistent to reboot only by the "log-level save" CLI command we will add the LOGLEVEL DB to the list of the dbies we flush before warm-reboot.
  During boot time, in the startup, the loglevel_db.json will load on the LOGLEVEL DB.

# 7 Yang model

  The following YANG model will be added in order to provide support for the logger:
   - sonic-logger.yang -> container LOGGER

   ```
    description "Logger Table yang Module for SONiC";

    container sonic-logger {

        container LOGGER {

            description "Logger table in config_db.json";

            list LOGGER_LIST {

                key "name";

                leaf name {
                    description "Component name in LOGGER table (example for component: orchagent, Syncd, SAI components).";
                    type string;
                }

                leaf loglevel {
                    description "The loglevel verbosity for the component";
                    mandatory true;
                    
                    type enumeration {
                    
                        enum SWSS_EMERG 
                        enum SWSS_ALERT;
                        enum SWSS_CRIT;
                        enum SWSS_ERROR;
                        enum SWSS_WARN;
                        enum SWSS_NOTICE;
                        enum SWSS_INFO;
                        enumSWSS_DEBUG;

                        enum SAI_LOG_LEVEL_CRITICAL;
                        enum SAI_LOG_LEVEL_ERROR;
                        enum SAI_LOG_LEVEL_WARN;
                        enum SAI_LOG_LEVEL_NOTICE;
                        enum SAI_LOG_LEVEL_INFO;
                        enum SAI_LOG_LEVEL_DEBUG;
                    }
                }

                leaf logoutput {
                    mandatory true;
                    type enumeration {
                        enum SYSLOG;
                        enum STDOUT;
                        enum STDERR;
                    }
                    default SYSLOG;
                }  
            }
        }
    }
   ```


# 8 Testing

## 8.1 update existing tests
  
  - Update logger tests.
  - Update other tests that use the logger table.

## 8.1 Unit Testing
  
  - Yang model tests:
    - Logger table with wrong loglevel, or with wrong logoutput
    - Logger table without loglevel or logoutput
    - Logger table with valid values

## 8.2 Manual Testing 

  - Verify the log level is persistent to cold/fast/warm reboot after the user runs "config save":
    - Change the log level for some component from Notice to Info.
    - Run "log-level save".
    - Verify the loglevel.json file was created.
    - Reboot.
    - Verify the log level is "Info".
  - Verify the log level is not persistent to cold/fast/warm reboot if the user didn't run "config save": 
    - Change the log level for some component from Notice to Info.
    - Reboot.
    - Verify the log level is "Notice".
  - Verify the log level returns to default ?????? after removing the "loglevel_db.json" file and reboot:
    - Change the log level for some component from Notice to Info.
    - Run "log-level save".
    - Delete loglevel_db.json file.
    - Reboot.
    - Verify the log level is "Notice".

# 9 Open issues

  ## 9.1 j2
  ## 9.2 factory reset
  ## 9.2 Support ZTP configuration


