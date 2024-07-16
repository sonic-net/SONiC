# SONiC Python logger enhancement #

## Table of Content

### Revision

### Scope

This document describes an enhancement to SONiC Python logger.

### Definitions/Abbreviations

Log identifier: The identifier of a logger instance. Log message printed by the logger instance usually contains the identifier.

### Overview

SONiC provides two Python logger implementations: `sonic_py_common.logger.Logger` and `sonic_py_common.syslogger.SysLogger`. Both of them do not provide the ability to change log level at real time. Sometimes, in order to get more debug information, developer has to manually change the log level in code on a running switch and restart the Python daemon. This is not convenient.

SONiC also provides a C/C++ logger implementation in `sonic-platform-common.common.logger.cpp`. This C/C++ logger implementation is also a wrapper of Linux standard `syslog` which is widely used by swss/syncd. It provides the ability to set log level on fly by starting a thread to listen to CONFIG DB LOGGER table change. SONiC infrastructure also provides the Python wrapper for `sonic-platform-common.common.logger.cpp` which is `swsscommon.Logger`. However, this logger implementation also has some drawbacks:


1. `swsscommon.Logger` assumes redis DB is ready to connect. This is a valid assumption for swss/syncd. But it is not good for a Python logger implementation because some Python script may be called before redis server starting.
2. `swsscommon.Logger` wraps Linux syslog which only support single log identifier for a daemon. 

So, `swsscommon.Logger` is not an option too.

This document describes a Python logger enhancement which allows user setting log level at run time.

### Requirements

- Allow user to change log level of `sonic_py_common.syslogger.SysLogger` at run time.
- Logger instance shall use default log level if redis server is not up.

Note: `sonic_py_common.logger.Logger` is not in the feature scope because it is going to be deprecated.

### Architecture Design

`swsscommon.Logger` depends on a thread to listen to CONFIG DB LOGGER table change. It refreshes log level for each logger instances once the thread detects a DB entry change. A thread is considered heavy in a python script, especially that there are many short and simple python scripts which also use logger. To keep python logger light weight, it uses a different design than `swsscommon.Logger`:

- `SysLogger` class shall be changed to a singleton.
- `SysLogger` instance shall load log level configuration from DB during initialization stage if DB configuration is available.
- `SysLogger` instance shall save log level configuration to DB during initialization stage if DB configuration is not available.
- Logger configuration shall be refreshed by CLI which send a SIGHUP signal to the daemon.

![python-logger-enhancement](/doc/syslog/images/python_logger_enhancement.svg)

### High-Level Design

#### SysLogger class change

- `SysLogger` class shall be changed to a singleton
- A new argument `enable_runtime_config` shall be added to `SysLogger.__init__`. Default to False. Daemons who want to enable runtime log configuration can set it to True.
- `SysLogger` instance shall load log level configuration from DB during initialization stage if `enable_runtime_config` is True and DB config is available.
- `SysLogger` instance shall save log level configuration to DB during initialization stage if `enable_runtime_config` is True and DB configuration is not available.
- A new class level method `update_log_level` shall be added to `SysLogger` class. This method handles load or save log level configuration logic.

SysLogger create flow:

![python-logger-create-flow](/doc/syslog/images/python_logger_create_flow.svg)

Refresh configuration flow:

![python-logger-refresh-config-flow](/doc/syslog/images/python_logger_refresh_config_flow.svg)

### SAI API

N/A

### Configuration and management

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

Currently, `swssloglevel` is used to update log level at run time. It relies on the thread running in `swsscommon.Logger` to refresh the log level of each logger instance. Since there is no such thread in python logger implementation, a new CLI shall be added to refresh the log level by sending signal to relevant daemon.

> Note: `swssloglevel` cannot send signal to daemons running in other container because it is actually a program installed in swss container.

config syslog level -c <component> -l <log_level> [--service <service_name>] [--program <program_name>] [--pid <pid>]

- "-c": component name or log identifier name. It is the key of LOGGER table.
- "-l": log level. One of "DEBUG", "INFO", "NOTICE", "WARN", "ERROR"
- "--service": container name. Optional. The signal will be sent to that container if present.
- "--program": program name. Optional, only applicable when --service is present. The signal will be sent to that program running in the service.
- "--pid": process ID. Optional. If --service is present, the signal will be sent to the PID running in the service; otherwise, the signal will be send to the PID running in host side.

Examples:
```
# Update the log level without refresh the configuration
config syslog level -c xcvrd -l DEBUG

# Update the log level and send SIGHUP to xcvrd running in PMON
config syslog level -c xcvrd -l DEBUG --service pmon --program xcvrd

# Update the log level and send SIGHUP to PID 20 running in PMON
config syslog level -c xcvrd -l DEBUG --service pmon --pid 20

# Update the log level and send SIGHUP to PID 20 running in host
config syslog level -c xcvrd -l DEBUG --pid 20

# Invalid, --program must be used together with --service
config syslog level -c xcvrd -l DEBUG --program xcvrd

# Invalid, --service must be used together with --pid or --program
config syslog level -c xcvrd -l DEBUG --service xcvrd
```

#### Config DB Enhancements

A new field shall be added to LOGGER table:

- require_manual_refresh: Python logger shall set this field to true. CPP logger shall not set this field.

The new field is for CLI to determine if it should send signal to the daemon. For a CPP logger, it is not necessary to do that because the thread running in `swsscommon.Logger` will handle it.

### Warmboot and Fastboot Design Impact

N/A

### Memory Consumption

N/A

### Restrictions/Limitations

N/A

### Testing Requirements/Design

#### Unit Test cases

TBD

#### System Test cases

TBD

### Open/Action items - if any
