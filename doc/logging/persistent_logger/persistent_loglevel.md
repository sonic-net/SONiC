# Persistent log level HLD

# High Level Design Document

#### Rev 0.1

# Table of Contents
- [Persistent log level HLD](#persistent-log-level-hld)
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
    - [3.1.1 Move Logger's tables which store in LOGLEVEL DB to CONFIG DB](#311-move-logger's-tables-which-store-in-loglevel-db-to-config-db)
    - [3.1.2 Update "swssloglevel" script](#312-update-"swssloglevel"-script)
    - [3.1.3 Make the log level persistent using the "config save" CLI command](#313-make-the-log-level-persistent-using-the-"config-save"-cli-command)
    - [3.1.4 Listener thread tables](#314-listener-thread-tables)
    - [3.1.5 Removing LOGLEVEL DB - phase 2](#315-removing-loglevel-db-phase-2)
  - [3.2 Persistent Logger flow](#32-persistent-logger-flow)
- [4 Flows](#4-flows)
  - [4.1 System init flow](#41-system-init-flow)
- [5 Cold and Fast Reboot Support](#5-cold-and-fast-reboot-support)
- [6 Warm Reboot Support](#6-warm-reboot-support)
  - [6.1 Support warm upgrade](#61-support-warm-upgrade)
- [7 Support downgrade](#7-support-warm-downgrade)
- [8 Yang model](#8-yang-model)
- [9 Testing](#8-testing)
  - [9.1 Unit Testing](#91-unit-testing)
  - [9.2 Manual Testing](#92-manual-testing)



# List of Tables
* [Table 1: Abbreviations](#definitionsabbreviation)


# List of Figures
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
- Warm/Fast reboot won't be impacted following this change.

# 3 Persistent log level design
## 3.1 High-level design

To make the loglevel persistent to reboot, we will move the Logger's tables in LOGLEVEL DB to CONFIG DB. Since the Config DB is already persistent, the log level will also be persistent to reboot. The log level will be saved using the "config save" CLI command.

We will split this design into two phases to keep the pr with a small content:

Phase 1: make the loglevel persistent by moving it to the CONFIG DB.

Phase 2: Removing LOGLEVEL DB and the jinja2 cache.

### 3.1.1 Move Logger's tables which store in LOGLEVEL DB to CONFIG DB

#### Current LOGLEVEL DB schema:

 ```json
{
  "orchagent": {
    "orchagent": {
      "LOGLEVEL": "INFO",
      "LOGOUTPUT": "SYSLOG"
    }
  },

  "SAI_API_BUFFER": {
    "SAI_API_BUFFER": {
      "LOGLEVEL": "SAI_LOG_LEVEL_NOTICE",
      "LOGOUTPUT": "SYSLOG"
    }
  },

  "JINJA2_CACHE": { 
    
  }
}
```

#### New CONFIG DB schema:

 - A new "LOGGER" table will be added to the CONFIG DB.
 - There will be a minor change in the table keys(instead of "{componentName}:{componentName}" the key will be  the "Logger:{componentName}").
 - The filed logoutput that indicates to which file to print the logs will also be persistent.

```json
{
  "LOGGER": {
    "orchagent": {
      "LOGLEVEL": "INFO",
      "LOGOUTPUT": "SYSLOG"
    },

    "SAI_API_BUFFER": {
      "LOGLEVEL": "INSAI_LOG_LEVEL_NOTICEFO",
      "LOGOUTPUT": "SYSLOG"
    }
  }
}
```

### 3.1.2 Update "swssloglevel" script

In the current implementation, the "swssloglevel" script sets the log level in the LOGLEVEL DB.
- We will update the script so that the log level will be saved in the CONFIG DB.
- To allow the user to set the default log level value for all the components, we will add a -d flag to the "swssloglevel" script.
  The default log levels are: SWSS_NOTICE, SAI_LOG_LEVEL_NOTICE.

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
         -d     return all components to default loglevel

Examples:
	swssloglevel -l NOTICE -c orchagent # set orchagent severity level to NOTICE
	swssloglevel -l SAI_LOG_LEVEL_ERROR -s -c SWITCH # set SAI_API_SWITCH severity to ERROR
	swssloglevel -l SAI_LOG_LEVEL_DEBUG -s -a # set all SAI_API_* severity to DEBUG
        swssloglevel -d # return all components to default loglevel
```
The change is the file: /sonic-swss-common/common/loglevel.cpp

### 3.1.3 Make the log level persistent using the "config save" CLI command

The content of the CONFIG DB will load to the config_db.json. This is our behavior today, and it remains as it is. If the user configures loglevel for some component and runs "config save" the loglevel will be persistent.

### 3.1.4 Listener thread tables

In the current implementation, each component has a listener thread that registers to the LOGLEVEL DB table. Each change in the LOGLEVEL DB table is caught by the thread and trigger handler that change the component's Logger configuration. We will keep the same behavior on the CONFIG DB by changing the "settingThread" function.
This change will impact the following components:

buffermgrd                    
coppmgrd                      
fdbsyncd                      
fpmsyncd                      
gearsyncd                     
intfmgrd                     
portsyncd                  
syncd                 
teammgrd                  
teamsyncd               
tlm_teamd                    
tunnelmgrd                 
vlanmgrd                      
vrfmgrd                      
vxlanmgrd                    
wjhd                 
nbrmgrd                 
neighsyncd                
orchagent                 
portmgrd  

The change is the file: /sonic-swss-common/common/logger.cpp


### 3.1.5 Removing LOGLEVEL DB

  - After moving the Logger's table from LOGLEVEL DB, the leftover in LOGLEVEL DB will be the JINJA2_CACHE key.
  - JINJA2_CACHE key is a bytecode cache for jinja2 template that stores bytecode in Redis. The JINJA2 cache was created to optimize the warm reboot performance.
  - After the jinja2 cache was created, we added other optimizations for the warm reboot and raised the concern that the jinja2 cache does not improve the warm reboot performance anymore. After we checked the warm reboot performance with and without the jinja2 cache and saw no difference between them, we recommend removing the jinja2 cache and the LOGLEVEL DB.

#### Removing LOGLEVEL DB from schema.h

 - Removing the LOGLEVEL DB from the dbies list.
 ```
 /***** DATABASE *****/

#define APPL_DB         0
#define ASIC_DB         1
#define COUNTERS_DB     2
#define LOGLEVEL_DB     3
#define CONFIG_DB       4
#define PFC_WD_DB       5
#define FLEX_COUNTER_DB 5
#define STATE_DB        6
#define SNMP_OVERLAY_DB 7
#define RESTAPI_DB      8
#define GB_ASIC_DB      9
#define GB_COUNTERS_DB  10
#define GB_FLEX_COUNTER_DB  11
#define CHASSIS_APP_DB      12
#define CHASSIS_STATE_DB    13
#define APPL_STATE_DB       14

```

#### Removing jinja2_cache

 - Removing /sonic-config-engine/build/lib/redis_bcc.py file.

#### Removing LOGLEVEL DB from dbies list

There are files (about 50 files) that contain the LOGLEVEL DB as part of a list of all the dbies. We will remove the LOGLEVEL DB from these files.

for example /sonic-swss-common/common/table.cpp:

```
  const TableNameSeparatorMap TableBase::tableNameSeparatorMap = {
   { APPL_DB,             TABLE_NAME_SEPARATOR_COLON },
   { ASIC_DB,             TABLE_NAME_SEPARATOR_COLON },
   { COUNTERS_DB,         TABLE_NAME_SEPARATOR_COLON },
   { LOGLEVEL_DB,         TABLE_NAME_SEPARATOR_COLON },
   { CONFIG_DB,           TABLE_NAME_SEPARATOR_VBAR  },
   { PFC_WD_DB,           TABLE_NAME_SEPARATOR_COLON },
   { FLEX_COUNTER_DB,     TABLE_NAME_SEPARATOR_COLON },
   { STATE_DB,            TABLE_NAME_SEPARATOR_VBAR  },
   { APPL_STATE_DB,       TABLE_NAME_SEPARATOR_COLON }
};
```

 - In addition we will remove the LOGLEVEL DB connector from /sonic-swss/fdbsyncd/fdbsyncd.cpp that not in use.

## 3.2 Persistent Logger flow

- Each component has a singleton Logger object with a log level property and listener thread.
- When a component writes a log message, the Logger writes the message only if the loglevel of the message is above the current loglevel property.
- When the user wants to set a new log level to a component, he uses the "swssloglevel" script. The "swssloglevel" script sets the new verbosity to the CONFIG DB (database #4).
- The CONFIG DB change triggers an event, which is caught by the listener thread.
- The listener thread changes the loglevel property of the Logger.
- The user can use the "config save" command to save the current loglevel and make it persistent. It will copy the CONFIG DB content to the config_db.json.

In addition to the log level, the CONFIG DB contains the log output file. After "config save" the log output will be persistent to reboot too.







![persistent logger flow](/doc/logging/persistent_logger/persistent-logger-flow.png)







# 4 Flows

## 4.1 System init flow

When the system startup and the Database container initialize, and the config_db.json loads to CONFIG DB.
 
  - There is a concern about the log level of messages written before the database container is initialized (if it exists). From my understanding, the RSYSLOG-CONFIG is up only after the DATABASE container, so there won't be logs before the config_db.json loads to the CONFIG DB. In case there are messages before the loading, the messages will be in the default log level.


# 5 Cold and Fast Reboot Support
  
  The current implementation support cold and fast reboot. Since in the cold and fast reboot, the CONFIG DB content is deleted, the user needs to run "config save" to make the log level persistent to cold and fast reboot.

# 6 Warm Reboot Support

  With the current implementation, we don't flush the CONFIG DB before warm-reboot, which means that if the user configures some loglevel (for example, debug), after warm-reboot, the system startup with the same configurable loglevel (debug).

## 6.1 Support warm upgrade

 Since we are not flushing the LOGLEVEL DB when we perform a warm upgrade, we need to update the db migrator.
  - Add LOGLEVEL DB connector in the db migrator.
  - In case of a warm upgrade, move Logger tables from LOGLEVEL DB to CONFIG DB (with a minor change in the key) and delete LOGLEVEL DB.
  - Exposing the "del" function from the swss-common/sonicv2-connector.h to the db migrator. 

# 7 Support downgrade

In the current implementation, after a cold/fast reboot, the CONFIG DB and the LOGLEVEL DB flush, and the config_db.json loads into the CONFIG DB.
In addition, in the current implementation, after a warm reboot, the CONFIG DB and the LOGLEVEL DB are not flush, and the config_db.json does not load into the CONFIG DB.
This current state leads us not fully support the downgrade.

Here are some scenarios to notice:
Scenario 1:
 1. We have the image with the feature.
    The CONFIG DB will contain the Logger tables, and the LOGLEVEL DB will be empty.
 2. We perform a downgrade.
    The CONFIG DB will not contain the Logger tables. In addition, new Logger tables with default values will be added to the LOGLEVEL DB. After the downgrade, the user will be able to change the loglevel.
 3. We perform warm-upgrade:
    The Logger tables that were created in the LOGLEVEL DB from step 1 will move to the CONFIG DB.

Scenario 2:
 1. We have the image with the feature.
    The CONFIG DB will contain the Logger tables, and the LOGLEVEL DB will be empty.
 2. We perform a downgrade.
    The CONFIG DB will not contain the Logger tables. In addition, new Logger tables with default values will be added to the LOGLEVEL DB. After the downgrade, the user will be able to change the loglevel.
 3. We perform a upgrade:
    New Logger tables with default values will be added to the CONFIG DB. 

Scenario 3:
 1. We have the image with the feature, and the user changes the loglevel of some components. For example, the user changes the orchagent loglevel to DEBUG.
 2. running "config save". The Logger tables are saved to the config_db.json and are persistent.
 3. We perform a downgrade.
    The CONFIG DB will contain the Logger tables from the config_db.json. In addition, new Logger tables with default values will be added to the LOGLEVEL DB. After the downgrade, the user will be able to change the loglevel.
 4. We perform warm-upgrade:
    The Logger tables from the LOGLEVEL DB will override the unused Logger tables of the CONFIG DB. 


# 8 Yang model

  The following YANG model will be added in order to provide support for the Logger:
   - sonic-logger.yang

   ```

    description "Logger Table yang Module for SONiC";
    
    typedef swss_loglevel {
        type enumeration {
            enum EMERG;
            enum ALERT;
            enum CRIT;
            enum ERROR;
            enum WARN;
            enum NOTICE;
            enum INFO;
            enum DEBUG;
        }
    }
    
    typedef sai_loglevel {
        type enumeration {
            enum SAI_LOG_LEVEL_CRITICAL;
            enum SAI_LOG_LEVEL_ERROR;
            enum SAI_LOG_LEVEL_WARN;
            enum SAI_LOG_LEVEL_NOTICE;
            enum SAI_LOG_LEVEL_INFO;
            enum SAI_LOG_LEVEL_DEBUG;
        }
    }
    
    container sonic-logger {

        container LOGGER {

            description "Logger table in config_db.json";

            list LOGGER_LIST {

                key "name";

                leaf name {
                    description "Component name in LOGGER table (example for component: orchagent, Syncd, SAI components).";
                    type string;
                }

                leaf LOGLEVEL {
                    description "The log verbosity for the component";
                    mandatory true;
                    type union {
                        type swss_loglevel;
                        type sai_loglevel;
                    }
                }

                leaf LOGOUTPUT {
                    type enumeration {
                        enum SYSLOG;
                        enum STDOUT;
                        enum STDERR;
                    }
                    default SYSLOG;
                }  
            }
            /* end of list LOGGER_LIST */
        }
        /* end of LOGGER container */
    }
    /* end of sonic-logger container */


   ```


# 9 Testing
  
## 9.1 Unit Testing

  - Update the existing test that uses the LOGLEVEL DB:
    /sonic-swss-common/tests/logger_ut.cpp

  - Verify the log levels of all components returns to default after running "swssloglevel -d":
    - Change the log level for some components from Notice to Info.
    - Run "swssloglevel -d".
    - Verify all components return to the default log level.

  - Yang model tests:
    - Logger table with a wrong loglevel, or with a wrong logoutput
    - Logger table without loglevel or logoutput fileds
    - Logger table with valid values

## 9.2 Manual Testing 

  - Verify the log level is persistent to cold/fast/warm reboot after the user runs "config save":
    - Change the log level for some component from Notice to Info.
    - Run "config save".
    - Verify the loglevel.json file was created.
    - Reboot.
    - Verify the log level is "Info".
  - Verify the log level is not persistent to cold/fast reboot if the user didn't run "config save": 
    - Change the log level for some components from Notice to Info.
    - Reboot.
    - Verify the log level is "Notice".
  - Verify that we able change the log level for all the components.
  - Verify the LOGLEVEL DB does not contain the Logger tables after a warm upgrade.
  - Verify the CONFIG DB contains the Logger tables after a warm upgrade.
  

