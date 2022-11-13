# Control SONiC behaviors with SYSTEM_DEFAULTS table

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

This document covers high level design of `SYSTEM_DEFAULTS` table in SONiC.

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

To have a better management of the flags, a new table `SYSTEM_DEFAULTS` is introduced in this design. 

## 5 Design ##

### 5.1 DB Schema

A new table `SYSTEM_DEFAULTS` is added into config_db.
```
    key             = SYSTEM_DEFAULTS|feature_name; feature name must bt unique

    ;field          = value
    status          = 1*255VCHAR ; The value is a string, which can be 'enable'/'disable', 'down'/'up' or any string.
    custom_field     = 1*255VCHAR ; The name of custom_field can be any custom string.
```
Below is a sample of `SYSTEM_DEFAULTS` table

```
"SYSTEM_DEFAULTS": {
        "tunnel_qos_remap": {
            "status": "enabled"
        }
        "default_bgp_status": {
            "status": "down"
        }
        "synchronous_mode": {
            "status": "enable"
        }
        "dhcp_server": {
            "status": "enable"
        }
    }
```

### 5.2 How to update flags in `SYSTEM_DEFAULTS` table

#### 5.2.1 Set default value with `init_cfg.json`

The default value of flags in `SYSTEM_DEFAULTS` table can be set in `init_cfg.json` and loaded into db at system startup. These flags are usually set at image being build, and are unlikely to change at runtime.
If the values in `config_db.json` is changed by user, it will not be rewritten back by `init_cfg.json` as `config_db.json` is loaded after `init_cfg.json` in [docker_image_ctl.j2](https://github.com/sonic-net/sonic-buildimage/blob/master/files/build_templates/docker_image_ctl.j2)

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
For example, to turn on/off the `tunnel_qos_remap` feature, a new section will be defined in `minigraph.xml`

```
  <SystemDefaultsDeclaration>
    <a:SystemDefaults xmlns:a="http://schemas.datacontract.org/2004/07/Microsoft.Search.Autopilot.Evolution">
		 <a:SystemDefault>
            <a:Name>TunnelQosRemapEnabled</a:Name>
            <a:Value>True</a:Value>
         </a:SystemDefault>
    </a:SystemDefaults>
</SystemDefaultsDeclaration>
```
The new section will be parsed by `minigraph.py`, and the parsed value will be merged with the values defined in `init_cfg.json`, and finally written into `config_db`. If there are duplicated entries in `init_cfg.json` and `minigraph.xml`, the values in `minigraph.xml` will overwritten the values defined in `init_cfg.json`.
#### 5.2.3 Update value directly in db memory
For some behavior change, we may don't have to interrupt dataplane. To support controlling SONiC behavior on-the-fly, we can update the value of flags in memory with tools like `sonic-cfggen`, `configlet` or `config apply-patch`.

### 5.3 How to consume flags in `SYSTEM_DEFAULTS` table

#### 5.3.1 Consume at service startup or reload
All of the flags in `SYSTEM_DEFAULTS` table can be consumed at service startup or reload as we do now. We can use the flags to render templates or control the running path of code.

#### 5.3.2 Consume on-the-fly without interrupting traffic
The `SYSTEM_DEFAULTS` table can be subscribed by components that are interested on the flags. Hence, the in-memory change of flags will be consumed by running service, and take effect without reloading if possible. 

## 6 Change required ##
### 6.1 Template update
1. Templates that generate default values in `DEVICE_METADATA|localhost` table are required to be updated. The generated flags will be put into `SYSTEM_DEFAULTS` table now.
2. Templates that depend on `DEVICE_METADATA|localhost` table are required to be updated.

### 6.2 Yang model update
A new Yang model is to be added to restrict the valid flags in `SYSTEM_DEFAULTS` table. The existing entries for flags in current [sonic-device_metadata.yang](https://github.com/sonic-net/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-device_metadata.yang) are to be removed.

### 6.3 Code change
1. Update `db_migrator.py` to migrate flags from `DEVICE_METADATA|localhost` table to `SYSTEM_DEFAULTS` table. Current flags include

|Flag|Source|
|--|--|
|default_bgp_status| From init_cfg.json, the value is determined by option shutdown_bgp_on_start when image being built|
|default_pfcwd_status|From init_cfg.json, the value is determined by option enable_pfcwd_on_start when image being built|
|synchronous_mode|From init_cfg.json, the value is determined by option include_p4rt when image being built|
|buffer_model|From init_cfg.json, the value is determined by option default_buffer_model when image being built|
|dhcp_server| Parse from minigraph.xml|


2. Add code to subscribe `SYSTEM_DEFAULTS` table to get the update notification for components that is interested in the `SYSTEM_DEFAULTS` change. Currently, all orchs and daemons don't support changing flag controlled behaviors without restarting service, so no code change is required for existing components.

## 7 Test requirement
TBA

 
