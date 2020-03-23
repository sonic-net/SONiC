# SONiC Port Configuration Refactor Design #

## Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

## 1. Overview

The file "port_config.ini" defines port name, index and other information. In current SONiC code, there is a module [portconfig.py](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py) to parse and collect all information in this file. However, there are also other places have code to parse "port_config.ini". To keep code clean, it would be better to make all those parse logic reuse [portconfig.py](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py).

There are also open PRs to begin transitioning from the "port_config.ini" file to a new "platform.json" file. So if we keep all parse logic in [portconfig.py](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py), it will be easy to keep backward compatible.

## 2. Changes in portconfig module

1. [portconfig.parse_port_config_file](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L28) return value should always contain the index of all ports even if "index" is not defined in "portconfig.ini" because port index is used in other module. If there is no "index" defined, a zero based auto-increment default value should be there.

## 3. Files that contain "port_config.ini" related logic

1. [daemon_base.py](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-daemon-base/sonic_daemon_base/daemon_base.py) in [sonic-daemon-base](https://github.com/Azure/sonic-buildimage/tree/master/src/sonic-daemon-base) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).
2. [sfputilbase.py](https://github.com/Azure/sonic-platform-common/blob/master/sonic_platform_base/sonic_sfp/sfputilbase.py) in [sonic-platform-common](https://github.com/Azure/sonic-platform-common) contains logic to parse "port_config.ini", it should be replaced by [portconfig.get_port_config](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L20).
3. [sfputilhelper.py](https://github.com/Azure/sonic-platform-common/blob/master/sonic_platform_base/sonic_sfp/sfputilhelper.py) in [sonic-platform-common](https://github.com/Azure/sonic-platform-common) contains logic to parse "port_config.ini", it should be replaced by [portconfig.get_port_config](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L20).
4. [main.py](https://github.com/Azure/sonic-utilities/blob/master/sfputil/main.py) in [sonic-utilities](https://github.com/Azure/sonic-utilities) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).
5. [util_base.py](https://github.com/Azure/sonic-utilities/blob/master/utilities_common/util_base.py) in [sonic-utilities](https://github.com/Azure/sonic-utilities) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/Azure/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).

There are also some vendor specified code contains "port_config.ini" related logic, those code should be refactored by each vendor.

## 4. Dependency

[portconfig.py](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py) is defined in [sonic-config-engine](https://github.com/Azure/sonic-buildimage/tree/master/src/sonic-config-engine). In order to reuse this module:

1. For those modules who have build-time unit test, they may declare sonic-config-engine as a build-time dependency in make rules.
2. For those modules who are installed in a docker, we must make sure sonic-config-engine is also installed in that docker, for example, pmon docker need reuse portconfig.py and it has sonic-config-engine installed.

## 5. Test Plan

This change should be verified on all Mellanox SKU with a stable 201911 image.

1. Run regression on t0/t1-lag topology.
2. Verify all sub-commands of "show interfaces".
3. Verify all sub-commands of "sfputil".
4. After system initialize, verify xcrvd pushed correct data to redis.
5. Insert/Remove modules, verify modules status change accordingly.
6. Kill xcrvd, verify related information is removed from redis database.
7. Verify xcrvd update dom info correctly.
