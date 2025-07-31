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

During SWSS start, the prebuilt [copp.json](https://github.com/sonic-net/sonic-swss/blob/201911/swssconfig/sample/00-copp.config.json) file is loaded as part of start script [swssconfig.sh](https://github.com/sonic-net/sonic-buildimage/blob/201911/dockers/docker-orchagent/swssconfig.sh) and written to APP DB. [CoppOrch](https://github.com/sonic-net/sonic-swss/blob/201911/orchagent/copporch.cpp) then translates it to Host trap/policer tables and programmed to SAI.

## Proposed behaviour

With the new proposal, the CoPP tables shall be part of Config DB instead of APP DB. The default CoPP json file shall be prebuilt to the image and read during initialization. Any Config DB entries present shall be configured overwriting the default CoPP tables. This also ensures backward compatibility. At a high-level, the following are the expected changes:

### Schema Changes

A new schema is defined for COPP tables that seperates Queue/Policer groups and Traps. More details are in the "Examples" section

### Config DB
```
key = "COPP_GROUP|name"
queue         = number; strict queue priority. Higher number means higher priority.
trap_action   = packet_action; trap action which will be applied to all trap_ids for this group.
trap_priority = trap_priority

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
```
key = "COPP_TRAP|name"
trap_ids      = name ; list of trap ids
trap_group    = name ; copp group name
```

### StateDB

```
key = "COPP_GROUP_TABLE|name"
state        = "ok"

key = "COPP_TRAP_TABLE|name"
state        = "ok"
```

### coppmgr
Introduce a *new* CoPP manager, that subscribes for the Config DB CoPP Tables and Feature Tables. Based on the feature enablement, ```coppmgr``` handles the logic to resolve whether a CoPP table shall be written to APP DB for orchagent consumption. Inorder to reduce changes to copporch and for backward compatibility during warmboot, ```coppmgr``` shall use the existing APP_DB schema and implement internal logic to convert the proposed ConfigDB entries to APP DB entries. Similar to existing swss managers, an entry with state "ok" shall be added to STATE_DB. `coppmgrd` must be started by [supervisord.conf](https://github.com/sonic-net/sonic-buildimage/blob/master/dockers/docker-orchagent/supervisord.conf) first, before any other process is started in swss. During init, ```coppmgr``` shall read the ```copp_cfg.json``` file and apply the default configuration. The default shall not be part of Config_DB entries. ```coppmgr``` shall also read from the config_db during init and apply the logic to merge if there are same entries within the ```copp_cfg.json``` file.

Trap name added to copp_cfg.json file has to match a feature name exist in FEATURE table in Config DB.
In order to handle traps which has no associated feature (such as arp, ip2me), a new field called "always_enabled" will be added to COPP_TRAP table in Config DB.

With the new "always_enabled" field, coppmgr will determine if a trap should be installed.

- If a trap has "always_enabled":"true" field, install it.

- If the associated feature is enabled, install the trap.

Now, traps which have no associated feature, will be installed only if "always_enabled" field value is "true".

### copporch
```copporch``` shall only be a consumer of APP DB CoPP Table. It is not expected to handle feature logic and the current handling of features like sFlow, NAT shall be revisited and removed to be added as part of ```coppmgr```. However `copporch` must be able to handle any new trap_id getting added or removed from an existing CoPP table, and handle attribute value set for a trap group

### swssconfig
Handling of CoPP config json file shall be removed from ```dockers/docker-orchagent/swssconfig.sh```

### 00-copp.config.json
This file shall be modified to be compatible to Config DB schema, currently placed at ```swssconfig/sample/00-copp.config.json```. It shall be renamed to ```copp_cfg.j2``` and moved to ```files/image_config/copp/copp_cfg.j2```

### copp_cfg.json
A new file ```copp_cfg.json``` shall be introduced to include default CoPP tables from copp_cfg.j2 placed under ```/etc/sonic```. This file shall be read by ```coppmgr``` during initialization.

### Default CoPP Tables
There are two proposals for loading the default CoPP Tables.

1. Add default CoPP Tables to be part of init_cfg.json. As part of the post start action, the Config DB shall be loaded with default CoPP tables and/or any previously configured CoPP tables as part of the following handler in ```files/build_templates/docker_image_ctl.j2```

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
However, this approach has the following limitations:

In warmboot scenarios, as init_cfg.json is not read during warmboot and may result in ***new*** CoPP Tables in the "to" image not getting applied.
In coldboot, if user saves the config and the new release happened to have new CoPP values, it will not be applied since previous default values are present in config_db

2. ```coppmgr``` reading directly from ```copp_cfg.json``` and apply the default CoPP Tables.

For this design, considering the limitations, proposal is to go ahead with second option.

## Warmboot and Backward Compatibility
It is desirable to have warmboot functionality from previous release versions of Sonic. Since the existing schema has COPP Group name/key with protocol names (e.g `"COPP_TABLE:trap.group.bgp.lacp"`, there is a limitation in adding any new protocol or trap to an existing CoPP group and seamlessly migrate. However, with this proposal, the following options are considered:

1. The implementation is to do a migration of APP DB entries to new schema.
2. Let ```db_migrator``` remove all previously saved APP_DB entries and let syncd reconcile and remove the TRAP entries during warmboot. Later, ```coppmgr``` can reapply the traps afresh. Also remove COPP_TABLES from being saved in [backup_database](https://github.com/sonic-net/sonic-utilities/blob/master/scripts/fast-reboot#L234). This may require additional tests to confirm system behaviour during warmboot.
3. Remove '00-copp.config.json' from being included for checksum calculation in ```files/build_scripts/generate_asic_config_checksum.py```

In addition, the implementation must ensure that backward compatibility is maintained. If the system is boot-up with an *old* config file, the default CoPP tables are to be loaded from ```copp_cfg.json``` and expected to work seamlessly.

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

The following flow captures scenarios for ```boot-up``` sequence and ```config reload```. Default CoPP Tables shall be present in ```copp_cfg.json``` and if the same entry is present in ```config_db.json```, it is expected to be overwritten by ```config_db``` entry. This model ensures user-configuration gets priority over default configuration.

![](https://github.com/sonic-net/SONiC/blob/master/images/copp/CoppInit_1.png)

## Copp Manager flow

The following flow captures CoPP manager functionality.

![](https://github.com/sonic-net/SONiC/blob/master/images/copp/CoppManager_1.png)

# Examples

### Config DB
```
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
            "trap_action":"trap",
            "trap_priority":"4",
        },

        "COPP_GROUP|queue4_group2": {
            "queue": "4",
            "trap_action":"trap",
            "trap_priority":"4",
        },

        "COPP_GROUP|queue4_group3": {
            "queue": "4",
            "trap_action":"copy",
            "trap_priority":"4",
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
            "trap_group": "queue4_group2"
        },

        "COPP_TRAP|arp": {
            "trap_ids": "arp_req,arp_resp,neigh_discovery",
            "trap_group": "queue4_group3",
            "always_enabled": "true"
        },

        "COPP_GROUP|queue1_group1": {
            "queue": "1",
            "trap_action":"trap",
            "trap_priority":"1",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"6000",
            "cbs":"6000",
            "red_action":"drop"
        },

        "COPP_TRAP|ip2me": {
            "trap_ids": "ip2me",
            "trap_group": "queue1_group1",
            "always_enabled": "true"
        },

        "COPP_TRAP|nat": {
            "trap_ids": "src_nat_miss,dest_nat_miss",
            "trap_group": "queue1_group1"
        },

        "COPP_GROUP|queue2_group1": {
            "queue": "2",
            "trap_action":"trap",
            "trap_priority":"1",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"5000",
            "cbs":"5000",
            "red_action":"drop",
            "genetlink_name":"psample",
            "genetlink_mcgrp_name":"packets"
        },

        "COPP_TRAP|sflow": {
            "trap_ids": "sample_packet",
            "trap_group": "queue2_group1"
        },
    }
```

 *queue4_group2 is added for backward compatibility. Refer "existing" APP_DB entries below

### APP DB

The following sample APP DB entries shall be created by `coppmgr` by merging the above Config DB entries

```
        "COPP_TABLE:queue4_group1": {
            "trap_ids": "bgp,bgpv6",
            "queue": "4",
            "trap_action":"trap",
            "trap_priority":"4",
        },

        "COPP_TABLE:queue4_group2": {
            "trap_ids": "lldp",
            "queue": "4",
            "trap_action":"trap",
            "trap_priority":"4",
        },

        "COPP_TABLE:queue4_group3": {
            "trap_ids": "arp_req,arp_resp,neigh_discovery",
            "queue": "4",
            "trap_action":"copy",
            "trap_priority":"4",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"600",
            "cbs":"600",
            "red_action":"drop"
        }
 ```

 ### APP DB (Existing in swss, For reference purpose only)

 ```
 [
    {
        "COPP_TABLE:default": {
            "queue": "0",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"600",
            "cbs":"600",
            "red_action":"drop"
        },
        "OP": "SET"
    },
    {
        "COPP_TABLE:trap.group.bgp.lacp": {
            "trap_ids": "bgp,bgpv6,lacp",
            "trap_action":"trap",
            "trap_priority":"4",
            "queue": "4"
        },
        "OP": "SET"
    },
    {
        "COPP_TABLE:trap.group.arp": {
            "trap_ids": "arp_req,arp_resp,neigh_discovery",
            "trap_action":"copy",
            "trap_priority":"4",
            "queue": "4",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"600",
            "cbs":"600",
            "red_action":"drop"
        },
        "OP": "SET"
    },
    {
        "COPP_TABLE:trap.group.lldp.dhcp.dhcpv6.udld": {
            "trap_ids": "lldp,dhcp,dhcpv6,udld",
            "trap_action":"trap",
            "trap_priority":"4",
            "queue": "4"
        },
        "OP": "SET"
    },
    {
        "COPP_TABLE:trap.group.nat.ip2me": {
            "trap_ids": "ip2me,src_nat_miss,dest_nat_miss",
            "trap_action":"trap",
            "trap_priority":"1",
            "queue": "1",
            "meter_type":"packets",
            "mode":"sr_tcm",
            "cir":"6000",
            "cbs":"6000",
            "red_action":"drop"
        },
        "OP": "SET"
    }
]
```

