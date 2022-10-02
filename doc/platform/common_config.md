## Feature Name
**Generalizing config.bcm support for BRCM silicons**

## High Level Design Document
**Rev 0.1**

## Table of Contents
 * [List of Tables](#list-of-tables)
 * [Revision](#revision)
 * [About This Manual](#about-this-manual)
 * [Scope](#scope)
 * [Requirements Overview](#requirements-overview)
    * [Functional Requirements](#functional-requirements)
 * [Supported Platforms](#supported-platforms)
 * [Design Detail](#design-overview)
 * [Serviceability and DEBUG](#serviceability-and-debug)
    * [Syslogs](#syslogs)
    * [Debug](#debug)
 * [Unit Test](#unit-test)


# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 11/03/2020  | Geans Pin          | Initial version                   |

# About this Manual
We added support for a per-switching silicon common config.bcm file to assist with silicon-wide application configuration settings for all affected Broadcom platforms. The infrastructure saves development time by allowing applications to refactor common settings in a single location, and allows for platform-specific overrides. 
  
# Scope
This document gives the details of Per-switching silicon Common config for Broadcom Supported Platforms implementation.


## 1 Requirements Overview


### 1.1	Functional Requirements
The functional requirements include :
- Create the common file in the device common directory for different  BRCM switch chip family

- Merge the common config from device common directory to ODM
platform specific config. Duplicate configuration entries in the platform specific file override entries in the common config.bcm

- The final config.bcm merged with common config is required to be copied to a shared folder for debugging   
  

## 2 Supported Platforms

Per-switching silicon Common config feature is supported on all of the Broadcom platform if the common config files are created in the device/broadcom/x86_64-broadcom_common. Following is the current supported common configuration :

```
|-- x86_64-broadcom_b77 -- broadcom-sonic-td3.config.bcm
|-- x86_64-broadcom_b85 -- broadcom-sonic-td2.config.bcm
|-- x86_64-broadcom_b87-- broadcom-sonic-td3.config.bcm
|-- x86_64-broadcom_b96-- broadcom-sonic-th.config.bcm
|-- x86_64-broadcom_b97-- broadcom-sonic-th2.config.bcm
|-- x86_64-broadcom_b98-- broadcom-sonic-th3.config.bcm
```
## 3 Design Detail
The main change of the design is in the SYNCD docker syncd/scripts/syncd_init_common.sh script along with common config being created in the device/broadcom/x86_64-broadcom_common/ folder. The design standardize the common file name as broadcom-sonic-{$chip_id}.config.bcm . Also, in the SYNCD docker-syncd-brcm.mk, we extern the common config directory path /usr/share/sonic/device/x86_64-broadcom_common from host to docker for script reference.

The design change for syncd_init_common.sh is targeted on the config_syncd_bcm() which is only used for BRCM switch chip. In the config_syncd_bcm() function, it will load the common silicon config.bcm file by looking for a *.bcm file in the  /usr/share/sonic/device/x86_64-broadcom_common/x86_64-broadcom_{$chip_id} folder where the $chip_id is the upper 3 nibbles of the switching silicon's device ID as listed in SDK/include/soc/devids.h. Then, merge common broadcom-sonic-{$chip_name}.config.bcm file with the existing platform specific config.bcm file in which the duplicate configuration entries in the platform specific file will override entries in the common broadcom-sonic-{$chip_name}.config.bcm file. 

Since the platform specific config.bcm is read only in docker, the design copies the platform specific config.bcm and sai.profile to /tmp for handling common config merge process. The /tmp/sai.profile will be modified to point to the merged config.bcm under/tmp directory. The following switch initialization will reference to the new merged config.bcm pointed by updated sai.profile from the /tmp directory.


## 4 Serviceability and DEBUG
### 4.1 Syslogs
During system booting syncd initialization, the Per-switching silicon common config design will log the common config merged information to the syslogs for identifying which common config be merged to the ODM config.bcm for syncd initialization.

### Examples:
```
Nov  3 09:19:25.373964 2020 sonic INFO syncd#supervisord: syncd Merging 
/usr/share/sonic/hwsku/td3-ix8a-bwde-48x25G+8x100G.config.bcm with
/usr/share/sonic/device/x86_64-broadcom_common/x86_64-broadcom_b77
/broadcom-sonic-td3.config.bcm, merge files stored in 
/tmp/td3-ix8a-bwde-48x25G+8x100G.config.bcm
```
### 4.2 Debug logs
The finial config.bcm and sai.profile will copy to the shared folder /var/run/sswsyncd/ in the syncd docker for 'show tech' debugging purpose. Developer can check the final config.bcm file for debugging from the show tech dump /sai/xxx.config.bcm.

### Examples:
- Issue 'show tech'
- Check sonic_dump_sonic_20201103_090412/sai/td3-ix8-48x25G+8x100G.config.bcm  
```
parity_correction=1  
flowtracker_enable=2  
flowtracker_max_flows=48000  
flowtracker_drop_monitor_enable=1  
flowtracker_export_interval_usecs=1000000  
flowtracker_max_export_pkt_length=9000  
flowtracker_fsp_reinject_max_length=128  
num_queues_pci=46  
num_queues_uc0=1  
num_queues_uc1=1  
sai_eapp_config_file=/etc/broadcom/eapps_cfg.json  
```

## 5 Scalability
NA
## 6 Unit Test
- Check the system status to make sure syncd initial success
- Check the syslog to make sure the common config merged to
   config.bcm successfully
- Check the final merged config.bcm dump from show tech dump 


