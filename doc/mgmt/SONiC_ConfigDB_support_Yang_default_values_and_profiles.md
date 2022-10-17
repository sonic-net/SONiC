# SONiC ConfigDB support Yang default values and profiles

## Table of Contents

- [SONiC ConfigDB support Yang default values and profiles](#sonic-configdb-support-yang-default-values-and-profiles)
  - [Table of Contents](#table-of-contents)
- [About this Manual](#about-this-manual)
  - [Terminologies](#terminologies)
  - [Problem Statement](#problem-statement)
- [1 Functional Requirement](#1-functional-requirement)
  - [1.1 swss-common return default value from Yang model](#11-swss-common-return-default-value-from-yang-model)
  - [1.2 swss-common return profile from profile DB](#12-swss-common-return-profile-from-profile-db)
- [2 Design](#2-design)
    - [Current design:](#current-design)
  - [2.1 Considerations](#21-considerations)
    - [How to get default value](#how-to-get-default-value)
    - [How to get profile](#how-to-get-profile)
    - [API compatibility](#api-compatibility)
  - [2.2 Other solutions for Yang model default value](#22-other-solutions-for-yang-model-default-value)
  - [2.3 New class](#23-new-class)
  - [2.4 Other code change](#24-other-code-change)
  - [2.5 Database Schema](#25-database-schema)
  - [2.6 Code example](#26-code-example)
- [3 Reboot](#3-reboot)
  - [3.1 Cold-reboot](#31-cold-reboot)
  - [3.2 Warm-reboot](#31-warm-reboot)
  - [3.3 Fast-reboot](#31-fast-reboot)
  - [3.4 Schema upgrade and DB migration](#34-schema-upgrade-and-db-migration)
- [4 Error handling](#4-error-handling)
- [5 Serviceability and Debug](#5-serviceability-and-debug)
- [6 Unit Test](#6-unit-test)
- [7 Migration steps](#7-migration-steps)
  - [7.1 Phase 1](#71-phase-1)
  - [7.2 Phase 2](#72-phase-2)
- [8 References](#8-references)
  - [SONiC YANG MODEL GUIDELINES](#sonic-yang-model-guidelines)
  - [System-wide Warmboot](#8-2-system-wide-warmboot)
  - [Fast-reboot Flow Improvements HLD](#8-3-fast-reboot-flow-improvements-hld)

# About this Manual

This document provides a detailed description on the new features for:

- Yang model default value.
- Profile DB.
- swss-common API change.

## Terminologies

- Yang model:
  
  - The Yang model define a hierarchical data structure.
  - SONiC Define config DB schema with Yang model, please refer to [SONiC YANG MODEL GUIDELINES](#7-1-sonic-yang-model-guidelines)

- Default value:
  
  - Yang model support define default value for configuration items.
  - For example, default value for nat_zone:
    
    ```
        leaf nat_zone {
            description "NAT Zone for the vlan interface";
            type uint8 {
                range "0..3" {
                    error-message "Invalid nat zone for the vlan interface.";
                    error-app-tag nat-zone-invalid;
                }
            }
                                default "0";
        }
    ```

- J2 template:
  
  - SONiC using Jinja2 template generate configuration files during deply minigraph.
  
  - For example, buffer config are rendered by J2 template:
    
    ```
        {%- set default_cable = '40m' %}
        {%- macro generate_buffer_pool_and_profiles() %}
            "BUFFER_POOL": {
                "ingress_lossless_pool": {
                    "size": "26531072",
                    "type": "ingress",
                    "mode": "dynamic",
                    "xoff": "6291456"
                },
                "egress_lossless_pool": {
                    "size": "32822528",
                    "type": "egress",
                    "mode": "static"
                }
            },
    
            ......
    
        {%- endmacro %}
    ```

- Profile
  
  - Profile is part of OS image, should upgrade with OS upgrade.
  - Profile are suggested values based on expirence.
  - User can overwrite profile.

## Problem Statement

- SONiC still using old default value and config from j2 template after OS upgrade:
  - Following config may update after OS upgrade:
    - Default value: defined in yang model.
    - Profile: defined in j2 template.
  - Currently all config stored in config DB, so above configs can't be update after OS upgrade.
- Potential risk, Yang model default value conflict with hardcoded value:
  - Default value hardcoded in source code.
  - Yang model default value does not be used.
- SONiC utilities not support get user config and all config:
  - Vender OS have different show command:
    - show running: only return user config.
    - show running all: return user config, default value from yang model, and config from j2 template.
  - Currently SONiC only support 'show running'
- DB migrator has complex logic and hardcoded config data:
  - DB migrator will be run in post startup action.
  - DB migrator complex logic and hardcoded config for migrate from every historical version to latest version. This will keep increase and difficult to maintance.

# 1 Functional Requirement

## 1.1 swss-common return default value from Yang model

- Return default value is optional.
  - Application can read config without default value, also can read config with default value.
- Backward compatibility with existing code and applications.

## 1.2 swss-common return profile from profile DB

- Buffer profile stored in profile tables.

- Return profile is optional.
  
  - Application can decide read config with profile or not:
    - When application read profile:
      - If user overwrite the profile, user config will be return.
      - If user not overwrite the profile, profile will be return.
      - If user 'delete' the profile, will return nothing.
    - When application not read profile, API will only return user config.
      - If user overwrite the profile, user config will be return.
      - If user not overwrite the profile, will return nothing.
      - If user 'delete' the profile, then there also will no user config exist, will return nothing.

- Backward compatibility with existing code and applications.
  
  - For backward compatibility, when initialize buffer config from minigraph, the BUFFER_POOL and BUFFER_PROFILE tables will be write to both config DB and profile DB.
  - After all code migrate to use profile DB, profile will only write to profile DB.
  - Profile support delete/revert operation:
    - In some user scenario, user need delete a profile, and also may add config back later.
    - For delete operation, data in profile table will not be delete, profile use PROFILE_DELETE table to handle delete/revert:
      - When delete a profile item, profile provider will add the item key to PROFILE_DELETE table.
      - When read profile, any key in PROFILE_DELETE will not exist in result.
      - When user set deleted item back, the item key will be remove from PROFILE_DELETE table. also the item will be write to config DB.
      - For example:
        - BUFFER_POOL table are profile:
          
          ```
          "BUFFER_POOL": {
          "ingress_lossless_pool": {
            "size": "26531072",
            "type": "ingress",
            "mode": "dynamic",
            "xoff": "6291456"
          },
          "egress_lossless_pool": {
            "size": "32822528",
            "type": "egress",
            "mode": "static"
          }
          }
          ```
        - SONiC CLI allow user to remove buffer pool to migrate from double-ingress-pool mode to single-ingress-pool mode.
        - 'config qos clear' will remove some buffer pool. 
        - When delete a profile item 'ingress_lossless_pool', the key of this item will be write to PROFILE_DELETE table. and swsscommon read API will not return this item anymore.
        - Revert operation: when user set buffer mode back, buffer manager will write the deleted item back, when this happen, the key of the item will be removed from PROFILE_DELETE table. and swsscommon read API will return this item.

# 2 Design

- Config DB design diagram:

<img src="./images/swss-common-layer.png"  />

- API design diagram:

<img src="./images/swss-common-default-value.png"  />

### Current design:

- Existing API keeps no change. 
- Add decorator API to return default value and profile data.
- Load yang model as lazy as possible, use cache to only load yang model once.

## 2.1 Considerations

### How to get default value

|                                                               | Pros                                              | Cons                                                                                                                                              |
| ------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Get default value from Yang model in read API.                | Redis config DB keeps no change.                  | 3 MB memory per-process because need load Yang model and reference libyang.<br>50ms to load yang model.<br>8ms to read default value 10000 times. |
| Write default value to default value DB when write config DB. | Better read performance, Less memory consumption. | Need add new Redis DB for default value.                                                                                                          |

### How to get profile

- Profile will stored in a new redis database 'PROFILE_DB', database index is 15.
- Profile DB tables will have exactly same name and schema with config DB tables.
- Data will read form profile DB with swsscommon API.
- Profile DB will save and persist for warm-reboot and fast-reboot.

### API compatibility

|                                                 | Pros                                                                            | Cons                                                                                                                                     |
| ----------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Change API to return default value and profile. | Less code change, all app will get default value and profile automatically.     | For default value, there are hardcoded default value may different with Yang model, new default value from config DB may cause code bug. |
| Existing API keeps no change.                   | When update existing code, can cleanup code to remove hard coded default value. | All apps need code update.                                                                                                               |

## 2.2 Other solutions for Yang model default value

|                                                                                                                                                                                                        | Pros                                                                                                                                                                                   | Cons                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1. All existing APIs change to return default value.<br>2. Add new API to get 'real' data from config DB, which not have default value.                                                                | Less code change, all app will get default value automatically.                                                                                                                        | 1. There are hardcoded default value in many different place, the default value of those code may different with default value from Yang model, so new default value from config DB may cause code bug, this is a potential risk.<br/>2. 3 MB memory per-process because need load Yang model.<br/>3. 0.05 second to load yang model |
| 1. Write API change: when write data to config DB, also write default value to 'Default_value_DB'.<br/>2. Read API change: read default value from 'Default_value_DB' and merge with config DB result. | 1. Less memory consumption and better performance when only call read API: read API no need to load yang model.<br/>2. Less code change, all app will get default value automatically. | Hardcoded default value code still need cleanup.                                                                                                                                                                                                                                                                                     |

## 2.3 New class

- YangModelLoader class
  
  - load table name to default value mapping to memory.

- DefaultValueProvider class
  
  - Find default value information by table name and config DB key
  - Merge default value to API result.

- ProfileProvider class
  
  - Read profile from profile DB.
  - Merge profile to API result.

- YangDefaultDecorator python class

- DecoratorTable c++ class

## 2.4 Other code change

- Add new methods to TableEntryEnumerable  interface:
  - virtual bool hget(const std::string &key, const std::string &field, std::string &value) = 0;

## 2.5 Database Schema

- All profile table will have exactly same schema with existing ConfigDB tables.
  
  - BUFFER_POOL
  - BUFFER_PROFILE

- PROFILE_DELETE Table:
  - For usage of this table, please refer to [Backward compatibility with existing code and applications.](#backward-compatibility-with-existing-code-and-applications)
  - This table is a config DB table, it will presist cross reboot. When re-render config, this table will be flushed as well as other config DB tables.
  - Yang model: [link](./sonic-profile-delete.yang "profile delete table")
  ```
  ; Key
  itemkey              = 1*256VCHAR          ; Deleted profile item key.
  ```

## 2.6 Code example

- Connector Decorator:
  
  ```
   from swsscommon.swsscommon import SonicV2Connector, ConfigDBConnector, YangDefaultDecorator
  
   conn = ConfigDBConnector()
   decorator = YangDefaultDecorator(conn)
   decorator.connect()
   decorator.get_table("VLAN_INTERFACE")
   decorator.get_entry("VLAN_INTERFACE", "Vlan1000")
   decorator.get_config()
  ```

- DecoratorTable:
  
  ```
   from swsscommon.swsscommon import DBConnector, Table, DecoratorTable 
  
   db = DBConnector("CONFIG_DB", 0)
   # Still can use Table to read user config:
   # table = Table(db, 'VLAN_INTERFACE')
   # Use DecoratorTable to read default value, profile and use config:
   table = DecoratorTable(db, 'VLAN_INTERFACE')
   table.get("Vlan1000")
  ```

# 3 Reboot


## 3.1 Cold-reboot

- Code-reboot will reload config from init_cfg.json and config_db.json.
- DB migrator will run after cold reboot, will handle profile schema and data upgrade in DB migrator.

## 3.2 Warm-reboot

- Profile DB will follow SONiC warm-reboot process, warm-reboot will save whole Redis DB to /host/warmboot/dump.rdb, please refer to [System-wide Warmboot](#8-2-system-wide-warmboot)
- DB migrator will run after warm reboot, will handle profile schema and data upgrade in DB migrator.

## 3.3 Fast-reboot

- Profile DB will follow SONiC fast-reboot process, please refer to [Fast-reboot Flow Improvements HLD](#8-3-fast-reboot-flow-improvements-hld)
- DB migrator will run after fast reboot, will handle profile schema and data upgrade in DB migrator.

## 3.4 Schema upgrade and DB migration

- DB migrator will re-render profile DB to handle schema change.
  - Profile DB will generate by sonic-cfggen command.
- DB migrator code will improve by deprate hardcoded config and complex upgrade logic.
- Some profile configuration change are disruptive, for example buffer config change,those change need fast-reboot/warm-reboot to make sure change refelected on ASIC.
- When upgrade from older version SONiC which not have profile DB:
  - The config DB will keep no change, all data in config DB will be treat as user config.
  - Profile DB will be created, and DB migrator will initialize Profile DB.
  - From user aspect:
   - All existing configs keeps no change.
   - There will be new config items, if new version of SONiC contains new config item in profile.

# 4 Error handling

- Load yang model: throw exception when found yang model data issue.
- swss-common API: if not found Yang model schema data for a given table name, write warning message to syslog.

# 5 Serviceability and Debug

- Debug version will write debug log to syslog.

# 6 Unit Test

- All new code will 100% covered by gtest or pytest test case.

# 7 Migration steps

## 7.1 Phase 1

- swss common API change:

  - support Yang model default value.
  - support profile value.

- Profile DB code change:

  - sonic-cfggen change to support generate profile to PROFILE_DB.
  - sonic-util change to support generate profile when load minigraph.
  - for backward compatibility, config tables still generate to CONFIG_DB.

## 7.2 Phase 2

- Update sonic cli.

  - Add 'show all config' command, which will show following config:
    - User config from config DB.
    - Yang model default value.
    - Profile.
  - Add 'show user config' command, which will only show user config.
  - For backward compatibility, 'show config' will mapping to 'show all config'.
  - This will improve user expirence for debug config related issue.

- Find out all projects need update by code scan:

  - Any project using swsssdk.
  - Any project using swss common c++ lib.
  - Any project using swss common python lib.

- Involve project owner to migrate to new API.

  - If project still using swsssdk, then switch to swsscommon with new API.
  - When migrate to new API, also clean up hardcoded default values.
  - Fix code in buffer manager for a special case for dynamic buffer profile.

- Buffer manager change to use profile table class.

  - After this, sonic-cfggen and sonic-util change to not generate profile to CONFIG_DB.

- Improve DB migrator.

  - Re-generate profile DB when OS version changed after warm-reboot.
  - Deprecate hardcoded profile configuration and profile migrate logic.

# 8 References

## SONiC YANG MODEL GUIDELINES

https://github.com/Azure/SONiC/blob/master/doc/mgmt/SONiC_YANG_Model_Guidelines.md

## System-wide Warmboot

https://github.com/sonic-net/SONiC/blob/master/doc/warm-reboot/system-warmboot.md

## Fast-reboot Flow Improvements HLD

https://github.com/sonic-net/SONiC/blob/master/doc/fast-reboot/Fast-reboot_Flow_Improvements_HLD.md