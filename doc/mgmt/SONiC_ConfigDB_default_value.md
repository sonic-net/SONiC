# ConfigDB default value from Yang model

## Table of Contents
- [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
    + [SONiC issue solved by this feature](#sonic-issue-solved-by-this-feature)
- [1 Functional Requirement](#1-functional-requirement)
    + [1.1 swss-common return default value from Yang model](#1-1-swss-common-return-default-value-from-yang-model)
- [2 Design](#2-design)
    + [2.1 Considerations](#2-1-considerations)
    + [2.2 New class](#2-2-new-class)
    + [2.3 Other code change](#2-3-other-code-change)
    + [2.4 Other solutions](#2-4-other-solutions)
    + [2.2 New class](#222-new-class)
- [3 Error handling](#3-error-handling)
- [4 Serviceability and Debug](#4-serviceability-and-debug)
- [5 Unit Test](#5-unit-test)
- [6 Migration steps](#6-migration-steps)
    + [6.1 Phase 1](#6-1-phase-1)
    + [6.2 Phase 1](#6-2-Phase-2)
- [7 References](#7-references)


# About this Manual
This document provides a detailed description on the new features for:
 - Get default value from Yang model.
 - swss-common API support read default value from config DB.

## SONiC issue solved by this feature
 - Potential risk: Yang model default value conflict with hardcoded value:
    - Default value hardcoded in source code.
    - Yang model default value not used.
 - SONiC utilities not support get default value:
   - Vender OS have different show command:
     - show running: return user config which not include default value.
     - show running all: return all config with default value.
   - Currently SONiC only support 'show running'

# 1 Functional Requirement
## 1.1 swss-common return default value from Yang model
 - Return default value is optional.
   - Application can read config without default value, also can read config with default value.
 - Backward compatibility with existed code and applications.

# 2 Design
 - Design diagram:

<img src="./images/swss-common-default-value.png"  />

## 2.1 Considerations
### How to get default value

|                                                              | Pros                                              | Cons                                                         |
| ------------------------------------------------------------ | ------------------------------------------------- | ------------------------------------------------------------ |
| Get default value from Yang model in read API.               | Redis config DB keeps no change.                  | 3 MB memory per-process because need load Yang model and reference libyang.<br>50ms to load yang model.<br>8ms to read default value 10000 times. |
| Write default value to default value DB when write config DB. | Better read performance, Less memory consumption. | Need add new Redis DB for default value.                     |

### API compatibility

|                                        | Pros                                                         | Cons                                                         |
| -------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Change API to return default value. | Less code change, all app will get default value automatically. | There are hardcoded default value may different with Yang model, new default value from config DB may cause code bug. |
| Existed API keeps no change.      | When update existed code, can cleanup code to remove hard coded default value. | All apps need code update.                                   |

### Current design:
   - Get default value from Yang model in read API.
   - Existed read API keeps no change. 


## 2.2 New class
 - YangModelLoader class
   - load table name to default value mapping to memory.

 - DefaultValueProvider class
   - Find default value information by table name and config DB key
   - Merge default value to API result.

 - DBDecorator interface
 - ConfigDBDecorator class
   - This class contains all logic and knowledge for apply default to config DB query result. 

## 2.3 Other code change
 - DBConnector class add new methods:
   - const std::shared_ptr<swss::DBDecorator> setDBDecorator(std::shared_ptr<swss::DBDecorator> &db_decorator);
   - const std::shared_ptr<swss::DBDecorator> getDBDecorator(swss::DBDecoratorType type) const;
   - const DecoratorMapping &getDBDecorators() const;

 - Following class will add new parameter to ctor:
   - ConfigDBConnector_Native
   - ConfigDBPipeConnector_Native
   - ConfigDBConnector

 - Existed ctor for following class will mark as depracated:
   - ConfigDBConnector_Native
   - ConfigDBPipeConnector_Native

## 2.4 Other solutions

|                                                              | Pros                                                         | Cons                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| 1. All existed APIs change to return default value.<br>2. Add new API to get 'real' data from config DB, which not have default value. | Less code change, all app will get default value automatically. | 1. There are hardcoded default value in many different place, the default value of those code may different with default value from Yang model, so new default value from config DB may cause code bug, this is a potential risk.<br/>2. 3 MB memory per-process because need load Yang model.<br/>3. 0.05 second to load yang model |
| 1. Write API change: when write data to config DB, also write default value to 'Default_value_DB'.<br/>2. Read API change: read default value from 'Default_value_DB' and merge with config DB result. | 1. Less memory consumption and better performance when only call read API: read API no need to load yang model.<br/>2. Less code change, all app will get default value automatically. | Hardcoded default value code still need cleanup.             |


# 3 Error handling
 - Load yang model: throw exception when found yang model data issue.
 - swss-common API: if not found Yang model schema data for a given table name, write warning message to syslog.

# 4 Serviceability and Debug
 - Debug version will write debug log to syslog.

# 5 Unit Test
 - All new code will 100% covered by gtest test case.
 - Add E2E test case for all new APIs.

# 6 Migration steps
## 6.1 Phase 1
 - swss common API change to support read default value.

## 6.1 Phase 2
 - Find out all projects need update by code scan:
   - Any project using swsssdk.
   - Any project using swss common c++ lib.
   - Any project using swss common python lib.

 - Involve project owner to migrate to new API.
   - If project still using swsssdk, then switch to swsscommon with new API.
   - When migrate to new API, also clean up hardcoded default values. 

# 7 References
## SONiC YANG MODEL GUIDELINES
https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md
