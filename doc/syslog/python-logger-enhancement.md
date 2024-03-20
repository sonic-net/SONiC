# SONiC Python logger enhancement #

## Table of Content

### Revision

### Scope

This document describes an enhancement to SONiC Python logger.

### Definitions/Abbreviations

N/A

### Overview

SONiC provides a Python logger implementation in `sonic_py_common.logger.Logger`. This implementation is a simple wrapper of Python standard package `syslog`. It does not provide the ability to change log level at real time. Sometimes, in order to get more debug information, developer has to manually change the log level in code on a running switch and restart the Python daemon. 

SONiC also provides a C/C++ logger implementation in `sonic-platform-common.common.logger.cpp`. This C/C++ logger implementation is also a wrapper of Linux standard `syslog` which is widely used by swss/syncd. Fortunately, it provides the ability to set log level on fly by starting a thread to listen to CONFIG DB LOGGER table change. SONiC infrastructure also provides the Python wrapper for `sonic-platform-common.common.logger.cpp` which is `swsscommon.Logger`.

The command to change log level of `swsscommon.Logger` is `swssloglevel`. A simple example:

```
swssloglevel -l NOTICE -c orchagent # set orchagent severity level to NOTICE
```

Based on the above, it is possible to change the implementation of `sonic_py_common.logger.Logger` and make it wrap `swsscommon.Logger` instead of `syslog`.  

### Requirements

- Allow user to change log level of `sonic_py_common.logger.Logger` at real time.

### Architecture Design

The current architecture is not changed. 

### High-Level Design

![python-logger-enhancement-chart](/doc/syslog/images/python_logger_enhancement.svg)

A new argument `enable_realtime_log_level` shall be added to `sonic_py_common.logger.Logger` __init__ function:

```python
class Logger:
    def __init__(self, log_identifier=None, log_facility=DEFAULT_LOG_FACILITY, log_option=DEFAULT_LOG_OPTION, enable_realtime_log_level=False):
        ...
```

For performance consideration, the value of `enable_realtime_log_level` is default to False. User must explicitly set it to True to enable this feature.

To use the logger:

```python

logger = Logger('<log_identifier>', enable_realtime_log_level=True)
```

To set log level to DEBUG:

```
swssloglevel -l DEBUG -c <log_identifier>
```

The interface of `sonic_py_common.logger.Logger` is completely backward compatible with its original ones.

####

### SAI API

N/A

### Configuration and management

#### Manifest (if the feature is an Application Extension)

N/A

#### CLI/YANG model Enhancements

No CLI change is needed, `swssloglevel` is already there.

#### Config DB Enhancements

N/A

### Warmboot and Fastboot Design Impact

N/A

### Memory Consumption

Enable this feature would start a thread for the logger instance. The new thread consumes extra but very limited memory.

### Restrictions/Limitations

N/A

### Testing Requirements/Design

#### Unit Test cases

TBD

#### System Test cases

TBD

### Open/Action items - if any
