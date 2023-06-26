# Custom SI settings for CMIS modules #

#### Rev 0.1

## Table of Contents
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [Definition](#definition)
- [References](#references)
- [About This Manual](#about-this-manual)
- [1 Introduction and Scope](#1-introduction-and-scope)
  - [1.1 Clause from CMIS5p0 spec for Signal Integrity](#11-clause-from-cmis5p0-spec-for-signal-integrity)
  - [1.2 Clause from CMIS5p0 spec for Explicit Control](#12-clause-from-cmis5p0-spec-for-explicit-control)
- [2 Requirements](#2-requirements)
- [3 Architecture Design](#3-architecture-design)
  - [3.1 TX_SETTING](#31-tx_setting)
  - [3.2 RX_SETTING](#32-rx_setting)
  - [3.3 GLOBAL_MEDIA_SETTINGS](#33-global_media_settings)
  - [3.4 PORT_MEDIA_SETTINGS](#34-port_media_settings)
  - [3.5 List of standard TX RX SI parameters](#35-list-of-standard-tx-rx-si-parameters)
  - [3.6 Sample Optics SI setting file](#36-sample-optics-si-setting-file)
- [4 High-Level Design](#4-high-level-design)
- [5 SAI API](#5-sai-api)
- [6 Configuration and management](#6-configuration-and-management)
- [7 Warmboot and Fastboot Design Impact](#7-warmboot-and-fastboot-design-impact)
- [8 Restrictions or Limitations](#8-restrictions-or-limitations)
- [9 Unit Test cases](#9-unit-test-cases)

### List of Tables
  * [Table 1: Definitions](#table-1-definitions)
  * [Table 2: References](#table-2-references)

### Revision
| Rev |     Date    |       Author                       | Change Description                  |
|:---:|:-----------:|:----------------------------------:|-------------------------------------|
| 0.1 | 05/05/2023  | Anoop Kamath                       | Initial version                       

### Definition

#### Table 1: Definitions
| **Term**       | **Definition**                                   |
| -------------- | ------------------------------------------------ |
| xcvrd          | Transceiver Daemon                               |
| CMIS           | Common Management Interface Specification        |
| DP             | Data Path                                        |
| DPInit         | Data-Path Initialization                         |
| QSFP-DD        | QSFP-Double Density (i.e. 400G) optical module   |
| SI             | Signal Integrity                                 |
| EC             | Explicit Control                                 |
| TX             | Transmit                                         |
| RX             | Recieve                                          |
| EQ             | Equalizer                                        |

### References

#### Table 2: References

| **Document**                                            | **Location**  |
|---------------------------------------------------------|---------------|
| CMIS v5 | [CMIS5p0.pdf](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf) |

### About This Manual
This is a high-level design document describing the way to apply custom SI settings for CMIS supported modules.

## 1 Introduction and Scope
Certain high-speed QSFP_DD, OSFP and QSFP modules require Signal Integrity (SI) settings to match platform media settings in order to achieve link stability, right tunning and optimal performance.

### 1.1 Clause from CMIS5p0 spec for Signal Integrity
Excerpt from CMIS5.0 spec providing definition of Signal Integrity:

![image](https://user-images.githubusercontent.com/115578705/236561523-8999b615-b271-4e28-9fbe-d0c9d414bdb8.png)

These SI settings can vary based on combination of the module vendor plus platform vendor. The module will have default TX/RX SI settings programmed in its EEPROM by module vendor, but platform vendor has provision to overwrite these settings to match their platform requirements. 
The host can apply new TX SI settings when TX Input Adaptive EQ is disabled for all TX Data Path lanes but RX SI settings can be applied directly. These TX/RX setting should be applied with Explicit Control bit is set to 1.

### 1.2 Clause from CMIS5p0 spec for Explicit Control
Excerpt from CMIS5.0 spec providing definition of Explicit Control:

![image](https://user-images.githubusercontent.com/115578705/236561421-d960d243-cd26-4087-88fe-c621867ffaa7.png)

## 2 Requirements
This feature would be enabled per platform basis. If platform wants to use this feature, they would need to provide optics_si_setting.json file during init for XCVRD to parse it. The SI parameters can be vendor and module specific. The vendor can populate desired SI param values in a JSON file. Provide an approach in the CMIS state machine to generate and apply host defined SI parameters to module eeprom. The Modules that do not support CMIS and not part of CMIS state machine are not in the scope of this document. 

![image](https://user-images.githubusercontent.com/115578705/236575703-aea7f377-ba5e-4e96-b18e-920f93e19774.png)

## 3 Architecture Design
The SI media setting file optics_si_setting.json needs to be defined by each platform_vendor that will need SI settings. All SKUs of the platform will share the same optics_si_setting.json file. If no file is found, then this mechanism will be ignored.

This file will have TX, RX setting blocks, and each block will have two subblocks: the first is global level setting and the next is port level setting. These subblocks will eventually contain per-lane SI parameter setting values based on the type of vendor and speed that are expected to be programmed. The SI settings will not depend on cable length.

### 3.1 TX_SETTING:   
This section will provide details on whether the TX EQ (TX input equalizer control) setting is FIXED or ADAPTIVE. Only adaptive EQ should be used for TX input, and it's enabled as the default setting in module. Fixed EQ is not recommended for TX direction and will not work until the SI/Hardware team explicitly recommends it.

If the EQ_FIXED flag is false or not present, then the SI param generation flow will come out of TX_SETTING and continue with the RX_SETTING block. But if the EQ_FIXED flag is true for TX_SETTING, then we need to disable AdaptiveInputEqEnableTx.

The TX Input EQ register control: Page 10h Byte 153 – 159 

| **Byte**       | **Field Name**                            |
| -------------- | ----------------------------------------- |
| 153            | AdaptiveInputEqEnableTx1..8 (lane 1-8)    |
| 154 - 155      | AdaptiveInputEqRecallTx1..8 (lane 1-8)    |
| 156 - 159      | FixedInputEqTargetTx1..8    (lane 1-8)    |

### 3.2 RX_SETTING:   
The RX_SETTING block contains the same sections as TX_SETTING, but the EQ_FIXED flag should always be true. The SI settings can be directly written and applied for RX output equalization.

The RX Output EQ register control: Page 10h Byte 162 – 173

| **Byte**       | **Field Name**                            |
| -------------- | ----------------------------------------- |
| 162 - 165      | OutputEqPreCursorTargetRx1..8 (lane 1-8)  |
| 166 - 169      | OutputEqPostCursorTargetRx1..8 (lane 1-8) |
| 170 - 173      | OutputAmplitudeTargetRx1..8    (lane 1-8) |

### 3.3 GLOBAL_MEDIA_SETTINGS:  
This block's first level of identification will be the range of port numbers. The ports can be defined as a range of 0-31 or a list of multiple ports: 1, 2, 3, or a list of ports in the range of 5–10, 25–31, matching the index number in the port_config.ini file. This port range will have a unique defined lane speed, which will have unique vendor and vendor part number entries supporting this speed. Module key will be created based on speed and vendor details.

Each vendor will have per-lane SI param attribute entries applicable for the identified port + speed for the platform vendor. This value will be searched through the module key.

### 3.4 PORT_MEDIA_SETTINGS:  
The entries in this block will be unique single port numbers. The control of SI attribute list generation search will reach the PORT_MEDIA_SETTINGS block only when no attribute list is generated in the GLOBAL_MEDIA_SETTINGS block.   

There will be unique speed and vendor/vendor_PN entries in each identified port block.

Default values can be platform defaults for multiple vendors in each section.

### 3.5 List of standard TX RX SI parameters
-  FixedInputEqTargetTx 
-  OutputEqPreCursorTargetRx 
-  OutputEqPostCursorTargetRx 
-  OutputAmplitudeTargetRx

### 3.6 Sample Optics SI setting file:
```
{
        "TX_SETTING": {
                "EQ_FIXED": "False",
                "GLOBAL_MEDIA_SETTINGS": {},
                "PORT_MEDIA_SETTINGS": {}
        },

        "RX_SETTING": {
                "EQ_FIXED": "True",
                "GLOBAL_MEDIA_SETTINGS": {
                        "0-20,21-24": {
                                "100G_SPEED": {
                                        "CREDO-CAC82XYXYXYXYXHW": {
                                                "OutputEqPreCursorTargetRx": {
                                                        "OutputEqPreCursorTargetRx1": 5,
                                                        "OutputEqPreCursorTargetRx2": 5,
                                                        "OutputEqPreCursorTargetRx3": 5,
                                                        "OutputEqPreCursorTargetRx4": 5,
                                                        "OutputEqPreCursorTargetRx5": 5,
                                                        "OutputEqPreCursorTargetRx6": 5,
                                                        "OutputEqPreCursorTargetRx7": 5,
                                                        "OutputEqPreCursorTargetRx8": 5
                                                }
                                        },
                                        "INNOLIGHT-X-XY123-XYZ": {
                                                "OutputEqPostCursorTargetRx": {
                                                        "OutputEqPostCursorTargetRx1": 8,
                                                        "OutputEqPostCursorTargetRx2": 8,
                                                        "OutputEqPostCursorTargetRx3": 8,
                                                        "OutputEqPostCursorTargetRx4": 8,
                                                        "OutputEqPostCursorTargetRx5": 8,
                                                        "OutputEqPostCursorTargetRx6": 8,
                                                        "OutputEqPostCursorTargetRx7": 8,
                                                        "OutputEqPostCursorTargetRx8": 8
                                                }
                                        },
                                        "Default": {
                                                "OutputEqPreCursorTargetRx": {
                                                        "OutputEqPreCursorTargetRx1": 9,
                                                        "OutputEqPreCursorTargetRx2": 9,
                                                        "OutputEqPreCursorTargetRx3": 9,
                                                        "OutputEqPreCursorTargetRx4": 9,
                                                        "OutputEqPreCursorTargetRx5": 9,
                                                        "OutputEqPreCursorTargetRx6": 9,
                                                        "OutputEqPreCursorTargetRx7": 9,
                                                        "OutputEqPreCursorTargetRx8": 9
                                                }

                                        }
                                }
                        },
                        "25,28,30": {
                                "100G_SPEED": {
                                        "Default": {
                                                "OutputAmplitudeTargetRx": {
                                                        "OutputAmplitudeTargetRx1": 7,
                                                        "OutputAmplitudeTargetRx2": 7,
                                                        "OutputAmplitudeTargetRx3": 7,
                                                        "OutputAmplitudeTargetRx4": 7,
                                                        "OutputAmplitudeTargetRx5": 7,
                                                        "OutputAmplitudeTargetRx6": 7,
                                                        "OutputAmplitudeTargetRx7": 7,
                                                        "OutputAmplitudeTargetRx8": 7
                                                }
                                        }
                                }
                        }
                },
                "PORT_MEDIA_SETTINGS": {
                        "31": {
                                "100G_SPEED": {
                                        "Default": {
                                                "OutputEqPostCursorTargetRx": {
                                                        "OutputEqPostCursorTargetRx1": 5,
                                                        "OutputEqPostCursorTargetRx2": 5,
                                                        "OutputEqPostCursorTargetRx3": 5,
                                                        "OutputEqPostCursorTargetRx4": 5,
                                                        "OutputEqPostCursorTargetRx5": 5,
                                                        "OutputEqPostCursorTargetRx6": 5,
                                                        "OutputEqPostCursorTargetRx7": 5,
                                                        "OutputEqPostCursorTargetRx8": 5
                                                }
                                        }
                                }
                        }
                }
        }
}
```

## 4 High-Level Design
Please refer below points in line with flow diagram.

1. When CMIS-supported module insertion happens in XCVRD, the module will progress to the AP_CONFIG state (after DP_DEINIT state) in the CMIS state machine. During which, when the module is in DataPathDeactivated or Disabled state, check if the optics_si_setting.json file is parsed successfully and if lane speed needs special Signal Integrity (SI) settings.

2. If both of the above conditions are met, then proceed to generate the key (module key) and retrieve the SI attribute list.  
  2.1. The JSON file has two directions (TX_SETTING and RX_SETTING) blocks. Each of these blocks contains sub-blocks of module vendors and other details that will help identify the best match to generate the SI attribute list, if applicable.  
  2.2.  The EQ_FIXED flag is required to validate if the TX input EQ (equalization) setting is adaptive or fixed. TX EQ settings are adaptive by default and should be disabled to apply host-defined SI settings. Currently, fixed EQ settings are not recommended for TX input EQ settings. This kind of validation is not required to apply RX EQ settings. If EQ_FIXED is set to true only, then flow will move ahead with list generation, or else it will return an empty list for the direction (TX/RX) setting (2.10).   
  2.3. Generate module key based on Data Path(DP) lane speed + module vendor name, + module vendor part number.    
  2.4. Using this module key (2.3), the search begins for the detected port in the GLOBAL_MEDIA_SETTINGS section of the applicable direction (TX/RX) setting block. If the module key matches any entries or any search that matches for (2.5) to (2.8) sections, then SI attributes from this section are copied to the SI param attribute list (2.9).   
  2.5. If no match happens in 2.4, reduce the search to module default + speed of the detected port in GLOBAL_MEDIA_SETTINGS  
  2.6. If no match happens in 2.5, reduce the search to the speed of the detected port in GLOBAL_MEDIA_SETTINGS  
  2.7. If no match happens in the GLOBAL_MEDIA_SETTINGS block, the search now begins in the PORT_MEDIA_SETTINGS block for the detected port. If no match happens in the PORT_MEDIA_SETTINGS block, the final search for the default block is done.  
  2.8. If no match happens to the default block, then an empty attribute list (2.10) is returned.

3. Get the attribute list and validate if the list is not empty, then proceed to process the SI setting param list. If the list is empty, continue with the AP_CONF (applying app code, EC = 0) and DP_INIT state in the CMIS state machine.

4. Apply the application code to the configuration with Explicit Control (EC) = 0, and commit to the activate state.  
Reference Register: Upper Page 10h bytes 145 –152 (desired ApSel Code)

5. Read and cache the default or active TX/RX SI settings. We need to cache the default values of the module. It's possible that we may not modify all the parameters. In such cases, we need to apply new SI values along with the default values that were already present. If we only apply the new values in Staged Control Set, the other values will be set to 0 in the Active Control Set. 
Reference Register: Upper Page 11h bytes 214 to 234

6. Update the new values from the attribute list (3) to the cached SI list (5).
  
7. Write new EQ settings to Staged Control Set 0. EQ settings include: new SI attribute list from (6), disabling adaptive TX input EQ settings if applicable. Apply application code to config with EC = 1 and commit to the active set.  
Reference Register: Upper Page 10h bytes 143 (Applying APSel Config using ApplyDPInit, Copying from Staged Control Set to Active Control Set).
Reference Register: Upper Page 10h bytes 145 –152 (desired ApSel Code).   
Reference Register: Upper page 10h byte 153-173 (desired Host defined SI settings for EC=1 mode)

8. Validate the config_status code, if the status is not config success, then force CMIS to reinit and retry. If the configuration fails after 3 retry attempts, print an error message and exit from initializing this port. If config_status is successful, then continue with the DP_INIT state in the CMIS state machine.  
Reference Register: Upper Page 11h Byte 202-205 (config_status register)

![CMIS_HLD2 drawio-2-2-6](https://github.com/AnoopKamath/SONiC/assets/115578705/c3014369-c45c-4601-b365-ec4c288fd4a3)

SI attribute generation flow:

![Untitled](https://github.com/AnoopKamath/SONiC/assets/115578705/92e0291d-8d76-4d20-a535-95ee30a9265e)

## 5 SAI API
There are no changes to SAI API

## 6 Configuration and management
There are no changes to any CLI/YANG model or Config DB enhancements. 

## 7 Warmboot and Fastboot Design Impact
There is no impact to Warmboot and Fastboot design. This feature is invoked as part of exisiting CMIS manager flow only

## 8 Restrictions or Limitations
If transceiver is not present:
 - All the workflows mentioned above will not invoke
Modules that do not support CMIS and not part of CMIS state machine are not in the scope of this document.

## 9 Unit Test cases
1. Check XCVRD/CMIS log if optics SI settings are succesfully applied for module which expect the SI settings.
2. Check XCVRD/CMIS log if optics SI settings are ignored for modules that dont expect the SI settings.
3. Validate no link flaps or link down once SI settings are applied
