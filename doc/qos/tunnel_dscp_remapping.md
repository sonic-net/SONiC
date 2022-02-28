# DSCP remapping for tunnel traffic

## 1 Table of Content ###

- [Revision](#11-revision)
- [Scope](#2-scope)
- [Definitions/Abbreviations](#3-definitionsabbreviations)
- [Overview](#4-overview)
- [Design](#5-design)
    - [SWSS Schema](#51-swss-schema)
        - [Define new table for mapping](#511-define-new-table-for-mapping)
        - [Update existing TUNNEL table](#512-update-existing-tunnel-table)
        - [Define new field for extra lossless queues](#513-define-new-field-for-extra-lossless-queues)
    - [SAI attribute](#52-sai-attribute)
    - [orchagent](#53-orchagent)
- [Test requirement](#6-test-requirement)
- [Open Questions](#7-open-questions)

### 1.1 Revision ###
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 |             | Bing Wang   | Initial version                   |


## 2 Scope ##

This document covers high level design of DSCP and TC remapping for tunnel traffic in SONiC.

## 3 Definitions/Abbreviations ##


| Term | Meaning |
|:--------:|:---------------------------------------------:|
| PFC | Priority-based Flow Control  |
| TC | Traffic class|
| DSCP| Differentiated Services Code Point |

## 4 Overview

The current QoS map architecture allows for port-based selection of each QoS map. However, we are not able to override the port-based QoS map for tunnel traffic. 
This design proposes a method to remapping DSCP and TC for IPinIP tunnel. 


## 5 Design ##

### 5.1 SWSS Schema
#### 5.1.1 Define new table for mapping
Update [qos_config.j2](https://github.com/Azure/sonic-buildimage/blob/master/files/build_templates/qos_config.j2) to generate 4 tables for remapping. Currently, the remapping is required in `dual-tor` scenario. So the tables are rendered into `config_db` only when `DEVICE_METADATA['localhost']['subtype'] = 'DualToR`. 

Please be noted that below config is to remap traffic in queue 3 to queue 2, and traffic in queue 4 to queue 6.
* Table for decap

    DSCP_TO_TC_MAP for mapping DSCP to TC

    ```json
    "DSCP_TO_TC_MAP": {
        "AZURE_TUNNEL": {
            "0": "1",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "1",
            "6": "6",
            "7": "1",
            "8": "0",
            "9": "1"
    }
    ```

    TC_TO_PRIORITY_GROUP_MAP for mappping TC to PG

    ```json
    "TC_TO_PRIORITY_GROUP_MAP": {
        "AZURE_TUNNEL": {
            "0": "0",
            "1": "0",
            "2": "0",
            "3": "2",
            "4": "6",
            "5": "0",
            "6": "0",
            "7": "7"
    }
    ```

* Table for encap

    TC_TO_QUEUE_MAP for remapping queue

    ```json
    "TC_TO_QUEUE_MAP": {
        "AZURE_TUNNEL": {
            "0": "0",
            "1": "1",
            "2": "1",
            "3": "2",
            "4": "6",
            "5": "5",
            "6": "1",
            "7": "7"
    }
    ``` 

    TC_TO_DSCP_MAP for rewriting DSCP
    ```json
    "TC_TO_DSCP_MAP": {
        "AZURE_TUNNEL": {
            "0": "8",
            "1": "0",
            "2": "0",
            "3": "2",
            "4": "6",
            "5": "46",
            "6": "0",
            "7": "48"
    }
    ```

    To support the new table, a new YANG model `sonic-tc-dscp.yang` is required 
#### 5.1.2 Update existing TUNNEL table
1. Change `dscp_mode` from `uniform` to `pipe` for TC remapping
2. Add TC remapping config if TC remapping is enabled

```json
    "TUNNEL": {
        "MuxTunnel0": {
            "dscp_mode": "pipe",
            "dst_ip": "10.1.0.32",
            "ecn_mode": "copy_from_outer",
            "encap_ecn_mode": "standard",
            "ttl_mode": "pipe",
            "tunnel_type": "IPINIP",
            "decap_dscp_to_tc_map": "[DSCP_TO_TC_MAP|AZURE_TUNNEL]",
            "decap_tc_to_pg_map": "[TC_TO_PRIORITY_GROUP_MAP|AZURE_TUNNEL]",
            "encap_tc_to_queue_map": "[TC_TO_QUEUE_MAP|AZURE_TUNNEL]",
            "encap_tc_color_to_dscp_map": "[TC_TO_DSCP_MAP|AZURE_TUNNEL]"
        }
    }
```

#### 5.1.3 Define new field for extra lossless queues
Two new fields are added to specify software or hardward PFC watchdog.

* `pfc_wd_sw_enable` Specify the queue(s) to enable software PFC watchdog
* `pfc_wd_hw_enable` Specify the queue(s) to enable hardware PFC watchdog.

In current version, software PFC watchdog will read field `pfc_enable` to determine PFCWD is enabled on which queue(s). To maintain compatible with current logic, `db_migrator` script is required to be updated.

```json
"PORT_QOS_MAP": {
        "Ethernet0": {
            "dscp_to_tc_map": "[DSCP_TO_TC_MAP|AZURE]",
            "pfc_enable": "3,4,2,6",
            "pfc_wd_sw_enable": "3,4",
            "pfc_wd_hw_enable": "2,6",
            "pfc_to_queue_map": "[MAP_PFC_PRIORITY_TO_QUEUE|AZURE]",
            "tc_to_pg_map": "[TC_TO_PRIORITY_GROUP_MAP|AZURE]",
            "tc_to_queue_map": "[TC_TO_QUEUE_MAP|AZURE]"
        }
}
```

To support new field `pfc_wd_sw_enable` and `pfc_wd_hw_enable`, [sonic-port-qos-map.yang](https://github.com/Azure/sonic-buildimage/blob/master/src/sonic-yang-models/yang-models/sonic-port-qos-map.yang) is required to be updated.

 
### 5.2 SAI attribute
TC remapping requires below SAI attributes change.
```cpp
    /**
     * @brief Enable TC AND COLOR -> DSCP MAP on tunnel at encapsulation (access-to-network) node to remark the DSCP in tunnel header
     */
    SAI_TUNNEL_ATTR_ENCAP_QOS_TC_AND_COLOR_TO_DSCP_MAP,

    /**
     * @brief Enable TC -> Queue MAP on tunnel encap
     */
    SAI_TUNNEL_ATTR_ENCAP_QOS_TC_TO_QUEUE_MAP,

    /**
     * @brief Enable DSCP -> TC MAP on tunnel at termination (Network-to-access) node. This map if configured overrides the port MAP
     */
    SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP,

    /**
     * @brief Enable TC -> Priority Group MAP. TC is derived from the tunnel MAP
     */
    SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP,
```
### 5.3 orchagent

Code change in orchagent

1. Update `tunneldecaporch` to read and set new tunnel attributes when creating decap tunnel.

    | Attribute |     Value    |  
    |---|-----------|
    | SAI_TUNNEL_ATTR_ENCAP_QOS_TC_AND_COLOR_TO_DSCP_MAP | [TC_TO_DSCP_MAP\|AZURE_TUNNEL]|
    | SAI_TUNNEL_ATTR_ENCAP_QOS_TC_TO_QUEUE_MAP | [TC_TO_QUEUE_MAP\|AZURE_TUNNEL] |
    
2. Update `create_tunnel` defined in `muxorch.cpp` to read and set new tunnel attributes when creating tunnel.
    | Attribute |     Value    |  
    |---|-----------|
    | SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP | [DSCP_TO_TC_MAP\|AZURE_TUNNEL]|
    | SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP | [TC_TO_PRIORITY_GROUP_MAP\|AZURE_TUNNEL |
## 6 Test requirement
All changes are to be covered by system test.
* Encap at standby side
    
    * Test case 1 Verify DSCP re-writing
    * test case 2 Verify traffic is egressed at expected queue
    * Test case 3 Verify PFC frame generation at expected queue

* Decap at active side

    * Test case 1 Verify packets egressed to server at expected queue
    * Test case 2 Verify PFC pause frame block expected queue
    * Test case 3 Verify PFC frame generation at expected queue


## 7 Open Questions


 