# SONiC Port Configuration Refactor Design #

## Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Junchao Chen  | Initial version                   |

## 1. Overview

The file "port_config.ini" defines port name, index and other information. In current SONiC code, there is a module [portconfig.py](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py) to parse and collect all information in this file. However, there are also other places have code to parse "port_config.ini". To keep code clean, it would be better to make all those parse logic reuse [portconfig.py](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py).

There are also open PRs to begin transitioning from the "port_config.ini" file to a new "platform.json" file. So if we keep all parse logic in [portconfig.py](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py), it will be easy to keep backward compatible.

## 2. Changes in portconfig module

1. [portconfig.parse_port_config_file](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L28) return value should always contain the index of all ports even if "index" is not defined in "port_config.ini" because port index is used in other module. If there is no "index" defined, a 1-based auto-increment default value should be there. For now, there are still a few SKUs provided port_config.ini file with 0-based port index, all those port_config.ini files should be changed to 1-based.

## 3. Files that contain "port_config.ini" related logic

1. [daemon_base.py](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-daemon-base/sonic_daemon_base/daemon_base.py) in [sonic-daemon-base](https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-daemon-base) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).
2. [sfputilbase.py](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_sfp/sfputilbase.py) in [sonic-platform-common](https://github.com/sonic-net/sonic-platform-common) contains logic to parse "port_config.ini", it should be replaced by [portconfig.get_port_config](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L20). Currently sfptutilbase.py keeps 3 dictionaries and 1 list to store information gets from port_config.ini file. We will keep the current data structure of sfputilbase.py to avoid introduce too much changes which means that we need transform the output of portconfig.py to the existing data structure.
3. [sfputilhelper.py](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_sfp/sfputilhelper.py) in [sonic-platform-common](https://github.com/sonic-net/sonic-platform-common) contains logic to parse "port_config.ini", it should be replaced by [portconfig.get_port_config](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L20). Since the current logic in sfputilhelper.py and sfputilbase.py are very similar, it is suggested to put the logic in a common place and reuse it.
4. [main.py](https://github.com/sonic-net/sonic-utilities/blob/master/sfputil/main.py) in [sonic-utilities](https://github.com/sonic-net/sonic-utilities) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).
5. [util_base.py](https://github.com/sonic-net/sonic-utilities/blob/master/utilities_common/util_base.py) in [sonic-utilities](https://github.com/sonic-net/sonic-utilities) contains logic to get file path of "port_config.ini", it should be replaced by [portconfig.get_port_config_file_name](https://github.com/sonic-net/sonic-buildimage/blob/142d45ce98008aac6437070a3a941083494b52a8/src/sonic-config-engine/portconfig.py#L6).

There are also some vendor specified code contains "port_config.ini" related logic, those code should be refactored by each vendor.

## 4. Dependency

[portconfig.py](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-config-engine/portconfig.py) is defined in [sonic-config-engine](https://github.com/sonic-net/sonic-buildimage/tree/master/src/sonic-config-engine). In order to reuse this module:

1. For those modules who have build-time unit test, they may declare sonic-config-engine as a build-time dependency in make rules.
2. For those modules who are installed in a docker, we must make sure sonic-config-engine is also installed in that docker, for example, pmon docker need reuse portconfig.py and it has sonic-config-engine installed.

## 5. Test Plan

This change should be verified on all Mellanox SKU with a stable 201911 image.

1. Run regression on t0/t1-lag topology, verify that the change won't break any existing test cases.
2. Test all sub-commands of "show interfaces". Compare sub-commands with/without this feature, verify the command outputs are the same.
3. Test all sub-commands of "sfputil". Compare sub-commands with/without this feature, verify the command outputs are the same. Verify "sfputil lpmode" and "sfputil reset", make sure it works on the correct interface.
4. After system initialize, verify xcrvd pushed correct data to redis.
5. Insert/Remove modules, verify modules status change accordingly.
6. Kill xcrvd, verify related information is removed from redis database.
7. Verify xcrvd update dom info correctly.
