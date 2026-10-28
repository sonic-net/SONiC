# Support BMC flows in SONiC

## 1. BMC and Redfish 
Board Management Controller (BMC) is a specialized microcontroller embedded on a motherboard. It manages the interface between system management software and hardware. BMC provides out-of-band management capabilities, allowing administrators to monitor and manage hardware remotely.
OpenBMC is an open-source project that provides a Linux-based firmware stack for Board Management Controllers (BMCs). It implements the Redfish standard, allowing for standardized and secure remote management of server hardware. In essence, OpenBMC serves as the software that runs on BMC hardware, utilizing the Redfish API to facilitate efficient hardware management.
Redfish is a standard for managing and interacting with hardware in a datacenter, designed to be simple, secure, and scalable. It works with BMC to provide a RESTful API for remote management of servers. Together, Redfish and BMC enable efficient and standardized hardware management.
In summary, NOS will deal with BMC through the redfish RESTful API.


## 2. BMC flows in SONiC
The implementation is straightforward: SONiC will incorporate a Redfish client as the underlying infrastructure to support the BMC action. This Redfish client object is implemented and initialized at runtime by SONiC itself. 
![general flow](https://github.com/yuazhe/SONiC/blob/90aa83c07c4ae9502a78bd33ce5dc8b8e41b8b7e/images/bmc/bmc_overall_flow.png)

## 3. BMC ip address initialization
This is the flow of the bmc ip address configuration: 
- device/platform/bmc.json contains bmc_if_name,bmc_if_addr,bmc_addr,bmc_net_mask
- src/sonic-py-common/sonic_py_common/device_info.py::get_bmc_data read the bmc.json  
- src/sonic-config-engine/sonic-cfggen::main call to device_info.get_bmc_data and write it to DEVICE_METADATA|bmc (This field will be added to DEVICE_METADATA )
- files/image_config/interfaces/interfaces.j2 read DEVICE_METADATA|bmc   write to /etc/network/interfaces:
```
auto usb0
iface usb0 inet static
    address <address>
    netmask <netmask>
```

![ip address init flow](https://github.com/yuazhe/SONiC/blob/c3912566a589767e43f12d822dc3611734ae84dc/images/bmc/bmc_ip_set_flow.png)


## 3. BMC firmware upgrade flow

It requires a new ComponenetBMC object to be added to the component.py

![firmware upgrade flow](https://github.com/yuazhe/SONiC/blob/90aa83c07c4ae9502a78bd33ce5dc8b8e41b8b7e/images/bmc/bmc_firmware_upgrade_flow.png)

## 4. Sonic-platform-common support for bmc

### 4.1 BMC redfish client
The redfish_client.py module provides the RedfishClient class, which facilitates BMC access via cURL requests to Redfish APIs. This class serves as a cURL wrapper for executing various Redfish commands. The class utilizes callback functions to obtain user credentials securely and supports asynchronous task monitoring to handle long-running operations like firmware updates and log dump.

Key functionalities:
1.	Session Management: Handles login and logout operations, ensuring secure sessions with the BMC. It manages tokens and session IDs, and automates re-login if tokens expire.
2.	Firmware Management: Supports listing, updating, and querying firmware versions using Redfish APIs.
3.	BMC Operations: Enables BMC reset requests, password changes, and triggering/debugging log dumps.
4.	Error Handling: Maps cURL error codes to RedfishClient error codes, and includes comprehensive error handling and logging.
5.	Security: Obfuscates sensitive information such as tokens and passwords in logs and command outputs.

### 4.2 BMC api scope
Because in SONiC, each command will be executed as a separate process, nothing will be shared between 2 commands. This requires 2 separate BMC RF sessions, so to avoid exhausting session numbers, we will have a logout call after each of the commands executed.
Thus, there will be a python decorator used for each API/fucntion, for both login and logout.
```
APIs inherited from Device Base
get_name()
get_presence()
get_model()
get_serial()
get_revision()
get_status()
is_replaceable()

BMC general APIs
Return dictionary (Manufacturer, Model, PartNumber, PowerState, SerialNumber) to show the eeprom info or exception with the failure reason 
Returns an empty dictionary {} if EEPROM information cannot be retrieved        
get_eeprom()

Return string to show the firmware version or exception with the failure reason         
Returns 'N/A' if the BMC firmware version cannot be retrieved       
get_version()

   
Returns: A tuple (ret, msg) where:
ret: An integer return code indicating success (0) or failure
msg: A string containing success message or error description      
reset_root_password()


Returns: A tuple (ret, (task_id, err_msg)) where:
ret: An integer return code indicating success (0) or failure
task_id: A string containing the Redfish task ID for monitoring
            the debug log dump operation. Returns '-1' on failure.
err_msg: A string containing error message if operation failed,
        None if successful 
trigger_bmc_debug_log_dump()

Returns: A tuple (ret, err_msg) where:
ret: An integer return code indicating success (0) or failure
err_msg: A string containing error message if operation failed            
get_bmc_debug_log_dump(task_id, filename, path)

param fw_image: string to indicate the path of the firmware image
Returns:A tuple (ret, msg) where:
ret: An integer return code indicating success (0) or failure
msg: A string containing status message about the firmware update
         
update_firmware(fw_image)

```

## 5. CLI commands
```
show platform bmc summary 
---------------------------
Manufacturer: XXXXX
Model: XXXXX
PartNumber: XXXXX
SerialNumber: XXXXX
PowerState: XXXXX
FirmwareVersion: XXXXX               

show platform firmware status
Component    Version                    Description
-----------  -------------------------  ----------------------------------------
ONIE         XXXXXXXXXXXXXXXXXXXXXXXXX  ONIE - Open Network Install Environment
SSD          XXXXXXXXXXXXXXXXXXXXXXXXX  SSD - Solid-State Drive
BIOS         XXXXXXXXXXXXXXXXXXXXXXXXX  BIOS - Basic Input/Output System
CPLD1        XXXXXXXXXXXXXXXXXXXXXXXXX  CPLD - Complex Programmable Logic Device
CPLD2        XXXXXXXXXXXXXXXXXXXXXXXXX  CPLD - Complex Programmable Logic Device
CPLD3        XXXXXXXXXXXXXXXXXXXXXXXXX  CPLD - Complex Programmable Logic Device
BMC          XXXXXXXXXXXXXXXXXXXXXXXXX  BMC – Board Management Controller

show platform bmc eeprom
---------------------------
Manufacturer: XXXXX
Model: XXXXX
PartNumber: XXXXX
PowerState: XXXXX
SerialNumber: XXXXX

config platform firmware install chassis component BMC fw -y ${BMC_IMAGE}

```

## 6. show techsupport
Bmc dump will be included in the show techsupport, trigger_bmc_debug_log_dump() and get_bmc_debug_log_dump() shall be called by the generate-dump script. 

### 6.1. Overview
The 'show techsupport' command is extended to collect BMC dump logs via Redfish API. 
This integration is non-blocking and asynchronous: 
It triggers a BMC dump task at the start of the script, then continues with regular 
system data collection. Before the script finishes, it collects the dump from BMC 
using the task ID previously received. 
The design ensures that BMC issues (timeouts, failures, unsupported platforms) 
do not block or interrupt the standard dump flow. 

### 6.2 High-Level Diagram
![show techsupport flow](https://github.com/sonic-net/SONiC/blob/30d7b3524e1e1f25abb4679f7ffa777eabe9f499/images/bmc/show_techsupport_flow.png)

### 6.3 Errors Handling: 
- generate_dump check whether BMC is suppported (via bmc.json file). If not, BMC logic is skipped. 
- Errors in BMC initialization, trigger, or collect phases are caught and logged. 
- The timeout in techsupport script for collect_bmc_dump is set to 60 seconds. 
In practice, the dump is typically ready before collection begins. 
Since SONiC’s full techsupport script duration is already ≥ 1m20s, 
the BMC dump is often complete before reaching the collect stage. 
If not yet, we will wait for it with 60s timeout (a fallback and rarely used). 

## 7. Fast/Warm/Cold boot and SONiC upgrade flow
In general, this flow are cpu method so they are independent of bmc, no performace impact.

## 8. Further enhancement

After community review, there are two improvements that will be made in the 202605 branch:

1. The Redfish client will be added to the platform common API, providing support for these APIs, and it will be easier to extend for vendor-specific use.
