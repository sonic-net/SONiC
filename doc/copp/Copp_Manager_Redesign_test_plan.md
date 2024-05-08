# Copp Manager Redesign Test Plan

## Related documents

| **Document Name** | **Link** |
|-------------------|----------|
| CoPP Manager Redesign HLD | []|


## Overview

In the previous design of Copp Manager, before installing a trap, CoppMgr checks if one of the following requirements is fulfilled:

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
The test will be supported on ptf32, ptf64, t1 and t2.


## Test cases
### Test cases #1 -  Verify 4 traps'default configuration
1. Verify the 4 traps(arp, lacp, udld, ip2me) are installed by sending traffic with the default config
   (For traffic validation, please see the Notes)

### Test cases #2 - Add a new trap
#### Pre-condition: The tested trap should be uninstalled on dut.
#### Since different vendor's ASIC might have some different invisible default traps will cause traffic to be trapped,
#### we also need to remove them.
#### For example: Remove ip2me because bgp traffic can fall back to ip2me trap then interfere following traffic tests
1. Set always_enabled of bgp to true with following cmds:
   
  + generate copp config file
```  
   cat copp_bgp.json
      {
       "COPP_TRAP": {
           "bgp": {
           "always_enabled": "true"
            }
        }
   }
```
   + config load copp_bgp.json -y
   
2. Verify the corresponding trap status is installed by sending traffic(For traffic validation, please see the Notes)
3. Recover the config

   
### Test cases #3 - Remove a trap by removing entry from feature table
#### Pre-condition: The tested trap has been installed on dut,  with always_enable true and the corresponding entry enabled.
#### Since different vendor's ASIC might have some different invisible default traps will cause traffic to be trapped,
#### we also need to remove them.
#### For example: Remove ip2me because bgp traffic can fall back to ip2me trap then interfere following traffic tests
Take bgp trap as example:
1. Set always_enabled of bgp to false (refer to test #2)
2. Remove bgp entry from feature table with CMD
   redis-cli -n 4 hdel "FEATURE|bgp" "auto_restart" "has_global_scope" "has_per_asic_scope" "has_timer" "high_mem_alert" "state" 
3. Verify the tested trap is uninstalled  by sending traffic (For traffic validation, please see the Notes)
5. Recover the config   


### Test cases #4 - Remove a trap by disabling feature table
#### Since different vendor's ASIC might have some different invisible default traps will cause traffic to be trapped,
#### we also need to remove them.
#### For example: Remove ip2me because bgp traffic can fall back to ip2me trap then interfere following traffic tests
Take bgp trap as an example:
1. Set always_enabled of bgp to false (refer to test #2)
2. Enable bgp in feature table: config feature state bgp enabled    
3. Verify the tested trap is installed by sending traffic (For traffic validation, please see the Notes)
4. Disable bgp in feature table: config feature state bgp disabled 
5. Verify the tested trap is uninstalled by sending traffic (For traffic validation, please see the Notes)
6. Recover the config


### Test cases #5 - Verify trap configuration is saved or not after reboot(reboot, fast-reboot, warm-reboot)
1. Set always_enabled of a trap(e.g.  bgp) to true
2. Config save -y
3. Do reboot randomly(reboot/warm-reboot/fast-reboot)
4. Verify configuration are saved successfully
5. Verify the trap status is installed by sending traffic (For traffic validation, please see the Notes)
6. Recover the config

### Notes
When validating traffic, we need to take care the following cases:
1. When the trap is added, the traffic(rx_pps) will be in the range [PPS_LIMIT_MIN, self.PPS_LIMIT_MAX]
2. When the trap is removed, the traffic(rx_pps) will be smaller than PPS_LIMIT_MIN
Usually when the trap is removed, we expect the traffic for the trap should be 0, but it might be trapped by other traps.
For example： If only remove BGP traffic, BPG traffic will be trapped by IP2ME, so the traffic will not be 0
