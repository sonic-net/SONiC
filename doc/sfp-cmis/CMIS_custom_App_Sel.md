# Custom APP SEL for CMIS modules #

#### Rev 0.1

## Table of Contents
- [List of Tables](#list-of-tables)
- [Revision](#revision)
- [Definition](#definition)
- [References](#references)
- [About This Manual](#about-this-manual)
- [1 Introduction and Scope](#1-introduction-and-scope)
  - [1.1 IEEE 802p3ck Requirements](#11-ieee-802p3ck-requirements)
  - [1.2 TP4](#12-tp4)
- [2 Requirements](#2-requirements)
- [3 Architecture Design](#3-architecture-design)
  - [3.1 CMIS Control of App Sel Mode](#31-cmis-control-of-app-sel-mode)
  - [3.2 Custom CMIS App Sel](#32-custom-cmis-app-sel)
  - [3.3 Sample Optics SI APP Sel file](#33-sample-optics-si-app-sel-file)
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
| 0.1 | 03/05/2025  | Anoop Kamath                       | Initial version                       

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

#### Table 2: References
| **Document**                                            | **Location**  |
|---------------------------------------------------------|---------------|
| CMIS v5 | [CMIS5p0.pdf](http://www.qsfp-dd.com/wp-content/uploads/2021/05/CMIS5p0.pdf) |
| IEEE 802 | [IEEE802.pdf](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9999414) |

### About This Manual
This is a high-level design document describing the way to apply custom APP SEL for CMIS supported modules. 

## 1 Introduction and Scope
Different electrical link lengths require different module settings.  
Short mode: Lower output voltage, used for C2M (Chip-to-Module) short-reach links.  
Long mode: Higher output voltage, used for C2M long-reach links.  
This impacts performance and helps avoid signal degradation for long-reach connections.

### 1.1 IEEE 802p3ck Requirements
IEEE Standard for Ethernet: Physical Layer Specifications and Management Parameters for 100 Gb/s, 200 Gb/s, and 400 Gb/s Electrical Interfaces Based on PAM4 signaling for 100 Gb/s.
It also defines 100Gb/s per lane electrical interface and specifies TP4 output characteristics for signal integrity.

Reference from IEEE 

![image](https://github.com/user-attachments/assets/c082e321-d020-4c1c-992b-00b590759e78)


### 1.2 TP4
TP4 (Test Point 4) is a reference point in high-speed electrical signaling, particularly in IEEE 802.3 Ethernet standards. 
It is used to define signal integrity requirements at the interface between an electrical host and an optical module (C2M - Chip-to-Module).

TP4 is the measurement point at the output of the module, where the signal is sent towards the host receiver. It is a key location for verifying signal integrity and compliance with IEEE 802.3ck specifications.

 Test Points in the IEEE 802.3 Standard:
1. TP0 – Transmitter input (inside the chip).
2. TP1a/TP1 – Input to the module (near-end of the module receiver).
3. TP2 – Inside the module (before the optical conversion).
4. TP3 – Optical output of the module (before optical fiber transmission).
5. TP4 – Electrical output of the module (signal going to the host receiver).

```
+----------------+                     +----------------------+
|   Host ASIC    |                     |   Optical Module     |
| (Electrical    |                     | (Electrical + Optical|
|    Side)       |                     |       Side)          |
|                |                     |                      |
|   TX  -------> |  ------TP0--------> |  RX                  |
|   RX  <------- |  <-----TP4--------- |  TX                  |
+----------------+                     +----------------------+
```

## 2 Requirements
This feature would be enabled on a per-platform basis. If a platform wants to use this feature, it must provide the optics_si_app_sel.json file during initialization for XCVRD to parse. The mode value will depend on the platform's TP4 measurement points. The CMIS state machine will be modified to support host-defined APP SEL and program the module EEPROM accordingly.

Modules that do not support CMIS and are not part of the CMIS state machine are out of the scope of this document.

NOTE:  
This feature modifies the TP4 settings, which can also be achieved by providing the optics_si_settings.json file. Consequently, it will modify the TX/RX Signal Integrity Controls on page 10h with the Explicit Control bit set.   
If the optics_si_settings.json file is found, the Custom App Sel feature will be disabled. 


## 3 Architecture Design
Each platform vendor that requires custom APP code settings must define the optics_si_app_sel.json file. All SKUs of the platform will share the same optics_si_app_sel.json file. If no file is found, this mechanism will be ignored.  
``` eg: /usr/share/sonic/device/{platform}/optics_si_app_sel.json  ```

This file will contain sections based on lane speed and port number. Inside the port block, there will be a mode with values:

0 - Short mode
1 - Long mode

Example of App Code advertised in module eeprom
```
Application Advertisement: 
400GAUI-4-L C2M (Annex 120G) - Host Assign (0x11) - 400G-FR4/400GBASE-FR4 (Cl 151) - Media Assign (0x11)
200GAUI-4 C2M (Annex 120E) - Host Assign (0x11) - 200GBASE-FR4 (Cl 122) - Media Assign (0x11)
100GAUI-1-L C2M (Annex 120G) - Host Assign (0xff) - 100G-FR/100GBASE-FR1 (Cl 140) - Media Assign (0xff)
CAUI-4 C2M (Annex 83E) with RS(528,514) FEC - Host Assign (0x11) - 100G CWDM4 MSA Spec - Media Assign (0x11)
400GAUI-4-S C2M (Annex 120G) - Host Assign (0x11) - 400G-FR4/400GBASE-FR4 (Cl 151) - Media Assign (0x11)
100GAUI-1-S C2M (Annex 120G) - Host Assign (0xff) - 100G-FR/100GBASE-FR1 (Cl 140) - Media Assign (0xff)

```
### 3.1 CMIS Control of App Sel Mode:
Current CMIS implementation:
1. The host device selects the desired mode using CMIS registers.
2. Modules report supported application modes via App Advertisements.
3. The host writes the desired mode into the Application Select field in CMIS.
4. The module applies the corresponding Tx/Rx equalization, power levels, and signal conditioning settings.

### 3.2 Custom CMIS App Sel:   
1. Generate an optics_si_app_sel.json file containing the desired app sel mode for different speeds, individual ports, or port ranges.
2. The port block will have mode values (0 - Short, 1 - Long). The file will be parsed during XCVRD initialization.
3. Similar to the existing flow where the device selects the desired app code, the new logic will determine the app sel code based on mode.
4. If a mode-based app sel is not found for a given speed/lane configuration, it will revert to the existing logic to select the first best match.
 
### 3.3 Sample Optics SI APP Sel file:
```json
{
        "GLOBAL_MEDIA_SETTINGS": {
                "0-17,19-24": {
                        "100G_SPEED": {
                                "Mode": 0
                         }
                }
                "25,28,30": {
                        "100G_SPEED": {
                                "Mode": 1
                        }
                }
                   
        }
}
```

## 4 High-Level Design

1.  When a CMIS-supported module is inserted in XCVRD, the module transitions to the CMIS_INSERTED state.
2. The get_cmis_application_desired() API loops through available App codes.
3. In the current design, the code selects the first best match based on Host Lane and Host Speed.
4. The proposed change introduces logic to check the app code and match the best App code, incorporating the mode parsed from the JSON file.

Current CMIS FSM :

 ```
CMIS_INSERTED → CMIS_DP_DEINIT → CMIS_STATE_AP_CONF → CMIS_STATE_DP_INIT → CMIS_TX_ON → CMIS_READY
       |                                 |
       V                                 V
[get desired mode]          [Write selected APP code to EEPROM]
           |
           V
[Best match from the available App codes]

```


Propsed CMIS FSM:

 ```
PARSE optics_si_app_sel.json -> SAVE PARSED DATA IN port_appl_sel_data

CMIS_INSERTED → CMIS_DP_DEINIT → CMIS_STATE_AP_CONF → CMIS_STATE_DP_INIT → CMIS_TX_ON → CMIS_READY
       |                                 |
       V                                 V
[get desired mode]          [Write selected APP code to EEPROM]
           |
           V
[Implement new logic to read the port_appl_sel_data and determine the mode.]
[Iterate through all available application codes to match the host speed, host lane, and media lane with either L or S mode.]
[If no match is found, revert to the previous logic to select the best match.]

```

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
1. Check XCVRD/CMIS log if optics App sel settings are succesfully applied for module which expect the mode settings.
2. Check XCVRD/CMIS log if optics App settings are ignored for modules that dont expect the App mode settings.
3. Validate no link flaps or link down once App settings are applied
