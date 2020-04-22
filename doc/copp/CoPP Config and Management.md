# Introduction

The scope of this document is to provide the requirements and a high-level design proposal for Sonic Control Plane Policing configuration and management.

# Requirements

The following are the high level requirements for CoPP/TRAP managment

1. CoPP Tables shall be part of the Config DB. Currently this is only present in APP DB
2. User shall be able to configure, modify CoPP table entries for various policing requirements
3. System shall be backward compatible with old Config DB without any CoPP Tables
4. A VS test must be added to verify the Config DB CoPP tables

# Design Proposal

## Current behaviour

During SWSS start, the prebuilt [copp.json](https://github.com/Azure/sonic-swss/blob/201911/swssconfig/sample/00-copp.config.json) file is loaded as part of start script [swssconfig.sh](https://github.com/Azure/sonic-buildimage/blob/201911/dockers/docker-orchagent/swssconfig.sh) and written to APP DB. [CoppOrch](https://github.com/Azure/sonic-swss/blob/201911/orchagent/copporch.cpp) then translates it to Host trap/policer tables and programmed to SAI.

## Proposed behaviour

With the new proposal, the CoPP tables shall be loaded to Config DB instead of APP DB. The default CoPP json file shall be prebuilt to the image and loaded during initialization. Any Config DB entries present shall be configured overwriting the default CoPP tables. This also ensures backward compatibility. At a high-level, the following are the expected changes:

### Schema Changes

### Config DB

```
key = "COPP|name"
name_list     = name | name,name_list
queue         = number; strict queue priority. Higher number means higher priority.
trap_ids      = name_list; 
trap_action   = packet_action; trap action which will be applied to all trap_ids.

;Settings for embedded policer. 
meter_type  = "packets" | "bytes"
mode        = "sr_tcm" | "tr_tcm" | "storm"
color       = "aware" | "blind"
cbs         = number ;packets or bytes depending on the meter_type value
cir         = number ;packets or bytes depending on the meter_type value
pbs         = number ;packets or bytes depending on the meter_type value
pir         = number ;packets or bytes depending on the meter_type value

green_action         = packet_action
yellow_action        = packet_action
red_action           = packet_action
genetlink_name       = genetlink_name ;[Optional] "psample" for sFlow 
genetlink_mcgrp_name = multicast group name; ;[Optional] "packets" for sFlow 
```

### StateDB

```
key = "COPP_TABLE|name"
state        = "ok"
```

### coppmgr
Introduce a *new* CoPP manager, that subscribes for the Config DB CoPP Tables and Feature Tables. Based on the feature enablement, ```coppmgr``` handles the logic to resolve whether a CoPP table shall be written to APP DB for orchagent consumption. In case if the feature requires adding only few attributes to an existing CoPP Table, ```coppmgr``` shall add the respective attributes to APP DB entry when the feature is enabled. Similar to existing swss managers, an entry with state "ok" shall be added to STATE_DB.

### copporch
```copporch``` shall only be a consumer of APP DB CoPP Table. It is not expected to handle feature logic and the current handling of features like sFlow, NAT shall be revisited and removed to be added as part of ```coppmgr```

### swssconfig
Handling of CoPP config json file shall be removed from ```dockers/docker-orchagent/swssconfig.sh```

### 00-copp.config.json
This file shall be modified to be compatible to Config DB schema, currently placed at ```swssconfig/sample/00-copp.config.json```. It shall be renamed to ```copp_config.j2``` and moved to ```files/build_templates/copp_config.j2```

### init_cfg.json
```init_cfg.json``` shall be extended to include default CoPP tables from copp_config.j2

### Default CoPP Tables
As part of the post start action, the Config DB shall be loaded with default CoPP tables and/or any previously configured CoPP tables as part of the following handler in ```files/build_templates/docker_image_ctl.j2```

```
    function postStartAction()
        ...
        if [ -r /etc/sonic/config_db.json ]; then
            sonic-cfggen -j /etc/sonic/config_db.json --write-to-db
            if [ -r /etc/sonic/init_cfg.json ]; then
                sonic-cfggen -j /etc/sonic/init_cfg.json -j /etc/sonic/config_db.json --write-to-db
            else
                sonic-cfggen -j /etc/sonic/config_db.json --write-to-db
            fi
        fi
```

## Warmboot and Backward Compatibility
The implementation must ensure that backward compatibility is maintained. If the system is boot-up with an *old* config file, the default CoPP tables are to be loaded from ```init_cfg.json``` and expected to work seamlessly.

The implementation must ensure Warmboot functionality is working as expected. During warmboot, the CoPP tables shall be present in APP DB and system is restored from the APP DB entries. At the time of this proposal, existing APP DB entries are expected to be the default entries and shall not have a conflict with Config DB entries [*TBD*]

## CLI
CLI support to add/modify CoPP tables OR providing show commands to display existing CoPP entries is not scoped as part of this design and can be taken up as future activity.

# Flows

The following flow diagram captures the control flow.

## Initial config

The following flow captures scenarios for ```boot-up``` sequence and ```config reload```. Default CoPP Tables shall be present in ```init_cfg.json``` and if the same entry is present in ```config_db.json```, it is expected to be overwritten by ```config_db``` entry. This model ensures user-configuration gets priority over default configuration.

![](https://github.com/Azure/SONiC/blob/master/images/copp/copp_init.png)

## Copp Manager flow

The following flow captures CoPP manager functionality. 

![](https://github.com/Azure/SONiC/blob/master/images/copp/copp_manager.png)
