## Feature Name
**Per-switching silicon Common config for Broadcom Supported Platforms**

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
 * [Serviceability and DEBUG](#serviceability-and-debug)
    * [Syslogs](#syslogs)
    * [Debug](#debug)
 * [Unit Test](#unit-test)


# Revision
| Rev |     Date    |       Author       | Change Description                |
|:---:|:-----------:|:------------------:|-----------------------------------|
| 0.1 | 11/03/2020  |  Systems Infra Team     | Initial version                   |

# About this Manual
We added support for a per-switching silicon common config.bcm file to assist with silicon-wide application configuration settings for all affected Broadcom platforms. The infrastructure saves development time by allowing applications to refactor common settings in a single location, and allows for platform-specific overrides. 
  
# Scope
This document gives the details of Per-switching silicon Common config for Broadcom Supported Platforms implementation.


## 1 Requirements Overview


### 1.1	Functional Requirements
The functional requirements include :
-  Load the common silicon config.bcm file by looking for a *.bcm file in the  /usr/share/sonic/device/x86_64-broadcom_common/broadcom-sonic-{$chip_id}  directory where the  $chip_id  is the upper 3 nibbles of the switching silicon's device ID as listed in SDK/include/soc/devids.h. 
and standardize on the common file name as  broadcom-sonic-<chip abbreviation>.config.bcm in this directory. This  file naming convention is not strictly enforced by the infrastructure, however. 
  
- Merge common  broadcom-sonic-<chip abbreviation>.config.bcm  file is with the existing platform specific  config.bcm  file. Duplicate configuration entries in the platform specific file override entries in the common  broadcom-sonic-<chip abbreviation>.config.bcm  file.

## 2 Supported Platforms

In Buzznik+ release, Per-switching silicon Common config is supported on all of the Broadcom platform if the common config files are created in the device/broadcom/x86_64-broadcom_common. Following is the current supported common configuration :
|-- x86_64-broadcom_b77
|   `-- broadcom-sonic-td3.config.bcm
|-- x86_64-broadcom_b85
|   `-- broadcom-sonic-td2.config.bcm
|-- x86_64-broadcom_b87
|   `-- broadcom-sonic-td3.config.bcm
|-- x86_64-broadcom_b96
|   `-- broadcom-sonic-th.config.bcm
|-- x86_64-broadcom_b97
|   `-- broadcom-sonic-th2.config.bcm
`-- x86_64-broadcom_b98
    `-- broadcom-sonic-th3.config.bcm


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
-	Check the system status to make sure syncd initial success
-   Check the syslog to make sure the common config merged to
     config.bcm successfully
-   Check the final merged config.bcm dump from show tech dump 

