## CMIS and C-CMIS support for ZR on SONiC

### Overview
Common Management Interface Specification (CMIS) is defined for pluggables or on-board modules to communicate with the registers. With a clear difinition of these registers, modules can set the configurations or get the status, to achieve the basic level of monitor and control. 

CMIS is widely used on modules based on a Two-Wire-Interface (TWI), including QSFP-DD, OSFP, COBO and QSFP modules. However, new requirements emerge with the introduction of coherent optical modules, such as 400G ZR. 400G ZR is the first type of modules to require definitions on coherent optical specifications, a field CMIS does not touch on. The development of C(coherent)-CMIS aims to solve this issue. It is based on CMIS but incroporates more definitions on registers in the extended space, regarding the emerging demands on coherent optics specifications.

The scope of this work is to develop APIs for both CMIS and C-CMIS to support 400G ZR modules on SONiC.

The rest of the article will discuss the following items:

- Layered architecture to access registers
- Definition on CMIS and C-CMIS registers
- Method to read from and write to registers
- High level functions

### Layered architecture to access registers
          ---------------------------
         |   High level functions    |
          ---------------------------
                /\            ||            
                ||            \/
             ---------------------
            | Decode       Encode |
             ---------------------
                /\            ||            
                ||            \/
            ------------------------
           | read_reg     write_reg |
            ------------------------               
                /\            ||            
                ||            \/
             ---------------------
            |   Module registers  |
             ---------------------           
                

### Definition on CMIS and C-CMIS registers
-  Memory structure and mapping
-  Module general information pages
-  VDM pages
-  C-CMIS related pages (Page 30h - 3fh)

### Method to read from and write to registers

#### Read and write registers
- read_reg
- write_reg
#### Encoding and decoding raw data
- read_reg_from_dict
- write_reg_from_dict

### High level functions

#### Get module basic information
- get_module_type
- get_module_status
- get_module_vendor
- get_module_part_number
- get_module_serial_number
- get_datapath_lane_status
- get_module_case_temp
- get_supply_3v3
- get_laser_temp
- get_tuning_status
- get_laser_freq
- get_TX_configured_power

#### Get VDM related information
- get_VDM

#### Get C-CMIS PM
- get_PM

#### Set module configuration, turn up
- set_low_power
- set_TX_power
- set_laser_freq







