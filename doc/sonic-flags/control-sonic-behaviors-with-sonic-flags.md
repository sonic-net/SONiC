# Control SONiC behaviors with FLAGS table

## 1 Table of Content ###

- [Revision](#11-revision)
- [Scope](#2-scope)
- [Definitions/Abbreviations](#3-definitionsabbreviations)
- [Overview](#4-overview)
- [Design](#5-design)
- [Change required](#6-change-required)
- [Test requirement](#7-test-requirement)


### 1.1 Revision ###
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Bing Wang   | Initial version                   |


## 2 Scope ##

This document covers high level design of `FLAGS` table in SONiC.

## 3 Definitions/Abbreviations ##


| Term | Meaning |
|:--------:|:---------------------------------------------:|
|  |  |


## 4 Overview

A number of flags are required to turn on/off certain feature or control the behaviors of various features in SONiC. Currently, these flags are put into `DEVICE_METADATA` table.

```
 "DEVICE_METADATA": {
        "localhost": {
            "default_bgp_status": "down",
            "default_pfcwd_status": "enable",
            "synchronous_mode": "enable",
            "dhcp_server": "enable"
        }
    }
```
As a result, the `DEVICE_METADATA` table is inflating rapidly as we are having more and more flags, although these flags seem not to be categorized into `DEVICE_METADATA` 

To have a better management of the flags, a new table `FLAGS` is introduced in this design. 

## 5 Design ##

### 5.1 DB Schema

A new table `FLAGS` is added into config_db.
```
    key             = FLAGS

    ;field          = value
    FLAG_NAME       = 1*255VCHAR ; FLAG_NAME must be unique, the value is a string, which can be 'enable'/'disable', 'down'/'up' or any string. 
```
Below is a sample of `FLAGS` table

```
"FLAGS": {
        "default_bgp_status": "down",
        "default_pfcwd_status": "enable",
        "synchronous_mode": "enable",
        "dhcp_server": "enable"
    }
```

### 5.2 How to update flags in `FLAGS` table

#### 5.2.1 Set default value with `init_cfg.json`

The default value of flags in `FLAGS` table can be set in `init_cfg.json` and loaded into db at system startup. These flags are usually set at image being build, and are unlikely to change at runtime.

If the values in `config_db.json` is changed by user, it will not be rewritten back by `init_cfg.json` as `config_db.json` is loaded after `init_cfg.json` in [docker_image_ctl.j2](https://github.com/Azure/sonic-buildimage/blob/master/files/build_templates/docker_image_ctl.j2)

```
if [ -r /etc/sonic/config_db$DEV.json ]; then
    if [ -r /etc/sonic/init_cfg.json ]; then
        $SONIC_CFGGEN -j /etc/sonic/init_cfg.json -j /etc/sonic/config_db$DEV.json --write-to-db
    else
        $SONIC_CFGGEN -j /etc/sonic/config_db$DEV.json --write-to-db
    fi
fi
```
For example, the value of `default_bgp_status` is down in `init_cfg.json` if `shutdown_bgp_on_start` is set to `y` when image is being built. If we modify the value of `default_bgp_status` in `config_db.json` to `up`, it will keep `up`.
#### 5.2.2 Parse from `minigraph.xml` when loading minigraph

For the flags that can be changed by reconfiguration, we can update entries in `minigraph.xml`, and parse the new values in to config_db with minigraph parser at reloading minigraph.

#### 5.2.3 Update value directly in db memory
For some behavior change, we may don't have to interrupt dataplane. To support controlling SONiC behavior on-the-fly, we can update the value of flags in memory with tools like `sonic-cfggen`, `configlet` or `config apply-patch`.

### 5.3 How to consume flags in `FLAGS` table

#### 5.3.1 Consume at service startup or reload
All of the flags in `FLAGS` table can be consumed at service startup or reload as we do now. We can use the flags to render templates or control the running path of code.

#### 5.3.2 Consume on-the-fly without interrupting traffic
The `FLAGS` table can be subscribed by components that are interested on the flags. Hence, the in-memory change of flags will be consumed by running service, and take effect without reloading if possible. 

## 6 Change required ##
### 6.1 Template update
1. Templates that generate default values in `DEVICE_METADATA|localhost` table are required to be updated. The generated flags will be put into `FLAGS` table now.
2. Templates that depend on `DEVICE_METADATA|localhost` table are required to be updated.

### 6.2 Yang model update
A new Yang model is to be added to restrict the valid flags in `FLAGS` table. The existing entries for flags in current [sonic-device_metadata.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-device_metadata.yang) are to be removed.

### 6.3 Code change
1. Update `db_migrator.py` to migrate flags from `DEVICE_METADATA|localhost` table to `FLAGS` table.
2. Update the code of component to subscribe `FLAGS` table to watch the update.

## 7 Test requirement
TBA

 