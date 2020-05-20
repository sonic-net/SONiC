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

A new schema is defined for COPP tables that seperates Queue/Policer groups and Traps. More details are in the "Examples" section

### Config DB
```
key = "COPP_GROUP|name"
queue         = number; strict queue priority. Higher number means higher priority.
action        = packet_action; trap action which will be applied to all trap_ids for this group.
priority      = trap_priority

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
```
```
key = "COPP_TRAP|name"
trap_ids      = name ; list of trap ids
trap_group    = name ; copp group name
genetlink_name       = genetlink_name ;[Optional] "psample" for sFlow 
genetlink_mcgrp_name = multicast group name; ;[Optional] "packets" for sFlow 
```

### StateDB

```
key = "COPP_GROUP_TABLE|name"
state        = "ok"

key = "COPP_TRAP_TABLE|name"
state        = "ok"
```

### coppmgr
Introduce a *new* CoPP manager, that subscribes for the Config DB CoPP Tables and Feature Tables. Based on the feature enablement, ```coppmgr``` handles the logic to resolve whether a CoPP table shall be written to APP DB for orchagent consumption. Inorder to reduce changes to copporch and for backward compatibility during warmboot, ```coppmgr``` shall use the existing APP_DB schema and implement internal logic to convert the proposed ConfigDB entries to APP DB entries. Similar to existing swss managers, an entry with state "ok" shall be added to STATE_DB.

### copporch
```copporch``` shall only be a consumer of APP DB CoPP Table. It is not expected to handle feature logic and the current handling of features like sFlow, NAT shall be revisited and removed to be added as part of ```coppmgr```. However `copporch` must be able to handle any new trap_id getting added or removed from an existing CoPP table, and handle attribute value set for a trap group

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
It is desirable to have warmboot functionality from previous release versions of Sonic. Since the existing schema has COPP Group name/key with protocol names (e.g `"COPP_TABLE:trap.group.bgp.lacp"`, there is a limitation in adding any new protocol or trap to an existing CoPP group and seamlessly migrate. However, with this proposal, the implementation is to do a migration of APP DB entries to new schema.

In addition, the implementation must ensure that backward compatibility is maintained. If the system is boot-up with an *old* config file, the default CoPP tables are to be loaded from ```init_cfg.json``` and expected to work seamlessly.

## Limitations
1. In case of downgrade, the config_db entries shall be present as stale entries as there is no subscribers for the table. Functionality would be same as supported by the downgraded version
2. This proposal expects the table names to be consistent across multiple releases. 
3. User is expected to resolve any conflicts, say for a trap id or group, that arises due to default values from the Sonic binary vs same trap or group currently or previously configured by the user.

## CLI
`show` commands to display CoPP group and CoPP entries shall be provided as part of this feature implementation.

CLI support to add/modify CoPP tables is not scoped as part of this design. In future, the following commands shall be supported:

1. User shall be able to change policer values for a queue
2. User shall be able to change the queue for a protocol/trap
3. User shall be able to delete a group/trap. 
    *In the current proposal, this would mean to keep the key in config_db with empty attributes.

# Flows

The following flow diagram captures the control flow.

## Initial config

The following flow captures scenarios for ```boot-up``` sequence and ```config reload```. Default CoPP Tables shall be present in ```init_cfg.json``` and if the same entry is present in ```config_db.json```, it is expected to be overwritten by ```config_db``` entry. This model ensures user-configuration gets priority over default configuration.

![](https://github.com/Azure/SONiC/blob/master/images/copp/copp_init.png)

## Copp Manager flow

The following flow captures CoPP manager functionality. 

![](https://github.com/Azure/SONiC/blob/master/images/copp/CoppManager_1.png)

# Examples

    {
        "COPP_GROUP|default": {
            "queue": "0",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"600",
            "cbs":"600",
            "red_action":"drop"
        },

        "COPP_GROUP|queue4_group1": {
            "queue": "4",
            "action":"trap",
            "priority":"4",
        },
        
        "COPP_GROUP|queue4_group2": {
            "queue": "4",
            "action":"copy",
            "priority":"4",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"600",
            "cbs":"600",
            "red_action":"drop"
        },

        "COPP_TRAP|bgp": {
            "trap_ids": "bgp,bgpv6",
            "trap_group": "queue4_group1"
        },

        "COPP_TRAP|lldp": {
            "trap_ids": "lldp",
            "trap_group": "queue4_group1"
        },
       
        "COPP_TRAP|arp": {
            "trap_ids": "arp_req,arp_resp,neigh_discovery",
            "trap_group": "queue4_group2"
        },

        "COPP_GROUP|queue1_group1": {
            "queue": "1",
            "action":"trap",
            "priority":"1",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"6000",
            "cbs":"6000",
            "red_action":"drop"
        },
         
        "COPP_TRAP|ip2me": {
            "trap_ids": "ip2me",
            "trap_group": "queue1_group1"
        },
        
        "COPP_TRAP|nat": {
            "trap_ids": "src_nat_miss,dest_nat_miss",
            "trap_group": "queue1_group1"
        },
        
        "COPP_GROUP|queue2_group1": {
            "queue": "2",
            "action":"trap",
            "priority":"1",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"5000",
            "cbs":"5000",
            "red_action":"drop",
        },

        "COPP_TRAP|sflow": {
            "trap_ids": "sample_packet",
            "trap_group": "queue2_group1"
            "genetlink_name":"psample",
            "genetlink_mcgrp_name":"packets"
        },
    }
