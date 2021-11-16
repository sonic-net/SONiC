# Copp Manager Redesign Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| CoPP Manager Redesign HLD | [https://github.com/noaOrMlnx/sonic-swss/blob/4865a8eb37444c2c070ef49cc69690e4295ce07d/doc/copp_redisgn.md](https://github.com/noaOrMlnx/sonic-swss/blob/4865a8eb37444c2c070ef49cc69690e4295ce07d/doc/copp_redisgn.md)|


## Overview

In the current design of Copp Manager, before installing a trap, CoppMgr checks if one of the following requirements is fulfilled:

1. Trap name is in the features table and enabled.
2. Trap name does not exist in the features table. (e.g. arp, lacp, udld, ip2me).

If both requirements above do not exist, the trap will not be installed.

An issue in the logic was exposed, when for sflow feature, the entry was deleted from the features table, but the trap was anyway installed. This case is not expected since we can't know if the feature is enabled or disabled.

The fix for the above issue will require a change in logic:

+ If the feature is disabled or does not have an entry in te features table, don't install the trap.
+ If the trap name does not exist in the features table, but the trap has a field which called "always_enabled" and it's value is "true", install the trap.
+ If there is a feature in the features table that is enabled, install the associated trap.
+ If there is a feature which is in state 'disabled', but the associated trap has "always_enabled": "true" field, install the trap.

In this way, we can avoid the unknown situation when the feature entry is deleted, but install the traps which have no feature entry.

NOTE: If a trap has "always_enabled":"true" field, we don't check the features table.

### Scope

The test is to verify the Copp Manager redesign logic for installing or uninstalling trap, when there are different configuration combinations for always_enabled and the feature of the corresponding trap.   

### Scale / Performance

No scale/performance test involved in this test plan

### Related **DUT** CLI commands

No CLI

### Related DUT configuration files

The traps configuration are saved to  /etc/sonic/copp_cfg.json.

```
    "COPP_TRAP": {
    "bgp": {
        "trap_ids": "bgp,bgpv6",
        "trap_group": "queue4_group1"
    },
    "arp": {
        "trap_ids": "arp_req,arp_resp,neigh_discovery",
        "trap_group": "queue4_group2",
        "always_enabled": "true"
    },
    "udld": {
	    "trap_ids": "udld",
	    "trap_group": "queue4_group3",
         "always_enabled": "true"
    },
    "ip2me": {
	    "trap_ids": "ip2me",
	    "trap_group": "queue1_group1",
         "always_enabled": "true"
    },
    "lacp": {
	    "trap_ids": "lacp",
	    "trap_group": "queue4_group1",
         "always_enabled": "true"
    }
}
```
### Supported topology
The test will be supported on any toplogy.


## Test cases
### Test cases #1 -  Verify 4 traps'default configuration
1. Run cmd: dump state copp trap_id(arp, lacp, udld, ip2me)
   + Verify the value of always_enalbed for the trap in CONFIG_FILE is true in the outputs
   + Verify the keys of APPL_DB and ASIC_DB for the trap id both have value in the outputs(It means the trap is installed, vice versa).
Plese refer to the outputs below
```
dump state copp lacp
{
    "lacp": {
        "CONFIG_DB": {
            "keys": [
                {
                    "COPP_TRAP|lacp": {
                        "trap_group": "queue4_group1",
                        "trap_ids": "lacp"
                    }
                },
                {
                    "COPP_GROUP|queue4_group1": {
                        "cbs": "600",
                        "cir": "600",
                        "color": "blind",
                        "meter_type": "packets",
                        "mode": "sr_tcm",
                        "queue": "4",
                        "red_action": "drop",
                        "trap_action": "trap",
                        "trap_priority": "4"
                    }
                }
            ],
            "tables_not_found": []
        },
        "APPL_DB": {
            "keys": [
                {
                    "COPP_TABLE:queue4_group1": {
                        "cbs": "600",
                        "cir": "600",
                        "color": "blind",
                        "meter_type": "packets",
                        "mode": "sr_tcm",
                        "queue": "4",
                        "red_action": "drop",
                        "trap_action": "trap",
                        "trap_ids": "bgp,bgpv6,lacp",
                        "trap_priority": "4"
                    }
                }
            ],
            "tables_not_found": []
        },
        "ASIC_DB": {
            "keys": [
                {
                    "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP:oid:0x22000000000d07": {
                        "SAI_HOSTIF_TRAP_ATTR_PACKET_ACTION": "SAI_PACKET_ACTION_TRAP",
                        "SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP": "oid:0x11000000000d03",
                        "SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE": "SAI_HOSTIF_TRAP_TYPE_LACP"
                    }
                },
                {
                    "ASIC_STATE:SAI_OBJECT_TYPE_HOSTIF_TRAP_GROUP:oid:0x11000000000d03": {
                        "SAI_HOSTIF_TRAP_GROUP_ATTR_POLICER": "oid:0x12000000000d04",
                        "SAI_HOSTIF_TRAP_GROUP_ATTR_QUEUE": "4"
                    }
                },
                {
                    "ASIC_STATE:SAI_OBJECT_TYPE_POLICER:oid:0x12000000000d04": {
                        "SAI_POLICER_ATTR_CBS": "600",
                        "SAI_POLICER_ATTR_CIR": "600",
                        "SAI_POLICER_ATTR_COLOR_SOURCE": "SAI_POLICER_COLOR_SOURCE_BLIND",
                        "SAI_POLICER_ATTR_METER_TYPE": "SAI_METER_TYPE_PACKETS",
                        "SAI_POLICER_ATTR_MODE": "SAI_POLICER_MODE_SR_TCM",
                        "SAI_POLICER_ATTR_RED_PACKET_ACTION": "SAI_PACKET_ACTION_DROP"
                    }
                },
                {
                    "ASIC_STATE:SAI_OBJECT_TYPE_QUEUE:oid:0x150000000007da": {
                        "NULL": "NULL",
                        "SAI_QUEUE_ATTR_INDEX": "4",
                        "SAI_QUEUE_ATTR_TYPE": "SAI_QUEUE_TYPE_UNICAST"
                    }
                }
            ],
            "tables_not_found": [],
            "vidtorid": {
                "oid:0x22000000000d07": "oid:0x100000022",
                "oid:0x11000000000d03": "oid:0x200000011",
                "oid:0x12000000000d04": "oid:0x200000012",
                "oid:0x150000000007da": "oid:0x1530000040015"
            }
        },
        "STATE_DB": {
            "keys": [
                {
                    "COPP_TRAP_TABLE|lacp": {
                        "state": "ok"
                    }
                },
                {
                    "COPP_GROUP_TABLE|queue4_group1": {
                        "state": "ok"
                    }
                }
            ],
            "tables_not_found": []
        },
        "CONFIG_FILE": {
            "keys": [
                {
                    "COPP_TRAP|lacp": {
                        "trap_ids": "lacp",
                        "trap_group": "queue4_group1",
                        "always_enabled": "true"
                    }
                },
                {
                    "COPP_GROUP|queue4_group1": {
                        "trap_action": "trap",
                        "trap_priority": "4",
                        "queue": "4"
                    }
                }
            ],
            "tables_not_found": []
        }
    }
}
```


### Test cases #2 - Add a new trap
#### Pre-condition: The tested trap should be uninstalled on dut,the corresponding entry should be removed form  feature table.
According to the configuration in the table below to check corresponding trap's status.
Take sflow trap and the first test in row 1 as an example:
1. Set always_enabled of sflow to true in /etc/sonic/copp_cfg.json
2. systemctl restart swss
3. Add the sflow in the feature table, and enable it with CMD:
   redis-cli -n 4 hset "FEATURE|sflow" "auto_restart" "enabled" "has_global_scope" "False" "has_per_asic_scope" "True" "has_timer" "False" "high_mem_alert" "disabled" "state" "enabled"
4. Verify the corresponding trap status is installed.    
5. Recover the config
6. Repeat step1 ~ step4 for left cases in the table below

| **No** | **always_enabled** | **The corresponding feature is defined in Feature table**  | **The corresponding feature is enabled or disabled** |**trap status** |
|-------------------|----------|-------------------|----------|----------|
| 1 | true | Y | enable | Installed | 
| 2 | ture | Y | disabled | Installed |
| 3 | true | N | / | Installed |
| 4 | false | Y | enable| Installed | 
| 5 | false | Y | disable | uninstalled | 
| 5 | false | N | / | uninstalled |
   
### Test cases #3 - Remove a trap
#### Pre-condition: The tested trap has been installed on dut,  with always_enable true and the corresponding entry enabled.
According to the configuration in the table below to check corresponding trap's status.
Take sflow trap and the first test in row 1 as an example:
1. Set always_enabled of sflow to false in /etc/sonic/copp_cfg.json
2. systemctl restart swss
3. Remove sflow from the feature table with CMD
   redis-cli -n 4 hdel "FEATURE|sflow" "auto_restart" "has_global_scope" "has_per_asic_scope" "has_timer" "high_mem_alert" "state" 
4. Verify the tested status of trap according to the table below
5. Recover the config   
6. Repeat step1 ~ step5 for left cases in the table below

| **No** | **always_enabled** | **The corresponding feature is defined in Feature table** | **The corresponding feature is defined in Feature table** |**trap status** |
|-------------------|----------|-------------------|----------|----------|
| 1 | false | N | / | uninstalled | 
| 2 | false | Y | disabled | uninstalled |
| 3 | false | Y | enabled | installed |
| 4 | true | Y | disabled | installed | 
| 5 | true | N | / | installed |
   
### Test cases #4 - Verify trap configuration is saved or not after reboot(reboot, fast-reboot, warm-reboot)
1. Set always_enabled of a trap(e.g.  sflow) to ture in /etc/sonic/copp_cfg.json
2. systemctl restart swss
3. Set feature state of a trap(e.g. sflow) to enable
4. Config save -y
5. Do reboot randomly(reboot/warm-reboot/fast-reboot)
6. Verify configuration are saved successfully

### Test cases #5 - Verify the trap's behaviors by switching the feature state
#### Pre-condition: The trap has been installed on dut,  with always_enable false and the corresponding entry is enabled.
1. Disable a trap (e.g. sflow) 
2. Enable the trap
3. Verify the trap is installed
