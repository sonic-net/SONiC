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
This document provides an overview of the implementation of making the SWSS Logger persistent for SWSS Syncd and SAI components.

# Motivation
Log level verbosity is part of the configuration of the OS. Today, the log level is not persistent and gets a default value after reboot. We have a requirement to add the option to save the log level in a persistent mode.

# todo update
# Definitions/Abbreviation
| Abbreviation  | Description                               |
|---------------|-------------------------------------------|
| SONiC         | Software for open networking in the cloud | 
| SAI           | Switch Abstraction Interface              |


# 1 Background
Today, the user can configure the log level verbosity to each component in SWSS, Syncd, and SAI. In order to configure the log level in runtime, the user uses the "swssloglevel" script. The script updates the LOGLEVEL DB with the new verbosity. After a reboot, the LOGLEVEL DB flushes, and the log level value of all components returns to default.

# 2 Requirements Overview

## 2.1 Functional requirements

The persistent Logger should meet the following high-level functional requirements:
- The user can decide whether he wants the log level to be persistent or not. The default will be no persistent.
- Not impact the fast and warm reboot performance.

# 3 Logger design
## 3.1 High-level design

We will add a new "log-level save" command to allow the user to save the log level.

Similar to the config_db.json, we will add a new loglevel_db.json:
- On startup: we will load the loglevel_db.json file into the LOGLEVEL DB.
- On "log-level save": We will copy the LOGLEVEL DB content into the loglevel_db.json.
- On "swssloglevel" (already implemented): We will save the log level to the LOGLEVEL DB.

### Another approach:
We considered another approach, to move the LOGLEVEL DB content into the Config DB. Since the Config DB is already persistent, the log level will also be persistent to reboot. The log level will be saved when using the "config save" CLI command. We discarded this approach to allow users to save the configuration without saving the log level.

## 3.2 Persistent logger flow

- Each component has a singleton Logger object with a log level property and listener thread.
- On startup:
  - The loglevel_db.json file is loaded into the LOGLEVEL DB during the init of database docker.
  - The loglevel property is set accordingly to the loglevel value on the LOGLEVEL DB.
- When a component writes a log message, the Logger writes the message only if the loglevel of the message is above the current loglevel property.
- When the user wants to set a new log level to a component, he uses the "swssloglevel" CLI command. The "swssloglevel" script sets the new verbosity to the LOGLEVEL DB (database #3).
- The LOGLEVEL DB change triggers an event, which is caught by the listener thread.
- The listener thread changes the loglevel property of the Logger.
- The user can use the "log-level save" command to save the current loglevel and make it persistent. It will copy the LOGLEVEL DB content into the loglevel_db.json.



![persistent logger flow](/doc/logging/persistent_logger/persistent_logger.png)


## 3.2 CLI commands

To save the LOGLEVEL DB content into the loglevel_db.json file:
```
admin@sonic:~$ log-level save
```

## 3.3 LOGLEVEL DB schema


```
admin@sonic:~$ redis-cli -n 3 HGETALL ‘orchagent:orchagent’

1) “LOGLEVEL”

2) “INFO”

3) “LOGOUTPUT”

4) “SYSLOG”
```
In addition to the log level, the LOGLEVEL DB contains the log output file. After "log-level save" the log output will be persistent to reboot too.

## loglevel_db.json
Similar to the config_db.json, we will add a new loglevel_db.json. The JSON file will be added to etc/sonic/loglevel_db.json.

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