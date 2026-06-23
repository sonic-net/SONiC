# Support BMC flows in SONiC

## 1. BMC and Redfish 
Board Management Controller (BMC) is a specialized microcontroller embedded on a motherboard. It manages the interface between system management software and hardware. BMC provides out-of-band management capabilities, allowing administrators to monitor and manage hardware remotely.
OpenBMC is an open-source project that provides a Linux-based firmware stack for Board Management Controllers (BMCs). It implements the Redfish standard, allowing for standardized and secure remote management of server hardware. In essence, OpenBMC serves as the software that runs on BMC hardware, utilizing the Redfish API to facilitate efficient hardware management.
Redfish is a standard for managing and interacting with hardware in a datacenter, designed to be simple, secure, and scalable. It works with BMC to provide a RESTful API for remote management of servers. Together, Redfish and BMC enable efficient and standardized hardware management.

In summary, when the BMC runs OpenBMC, the Switch-Host NOS interacts with the BMC through the Redfish RESTful API.

When the BMC runs SONiC OS, the Switch-Host NOS interacts with the BMC through Redis over the host–BMC link (`usb0`). The host connects to the Redis instance on the BMC and reads platform data.

The host selects the communication path at runtime based on `DEVICE_METADATA|bmc.os`.


## 2. BMC flows in SONiC

SONiC supports two BMC operating-system cases on the Switch-Host side:

| BMC OS | Transport | Client on Switch-Host |
|--------|-----------|------------------------|
| **OpenBMC** | Redfish over `usb0` / `bmc_addr` | `RedfishClient` (`redfish_client.py`) |
| **SONiC** (default) | Redis over `usb0` / `bmc_addr` | Remote STATE_DB connector (`db_connect_remote`) |

For **OpenBMC**, SONiC incorporates a Redfish client as the underlying infrastructure to support BMC actions.

![general flow](https://github.com/yuazhe/SONiC/blob/90aa83c07c4ae9502a78bd33ce5dc8b8e41b8b7e/images/bmc/bmc_overall_flow.png)

For **SONiC BMC**, the host opens a TCP connection to the BMC Redis instance (STATE_DB, db 6), using the same `bmc_addr` from `bmc.json` / `DEVICE_METADATA|bmc`.
On Switch-BMC systems, Redis is bound to the BMC link IP at startup (see `dockers/docker-database/docker-database-init.sh` and `dockers/docker-database/supervisord.conf.j2`).

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


## 3. BMC firmware upgrade flow (OpenBMC only)

It requires a new ComponenetBMC object to be added to the component.py

![firmware upgrade flow](https://github.com/yuazhe/SONiC/blob/90aa83c07c4ae9502a78bd33ce5dc8b8e41b8b7e/images/bmc/bmc_firmware_upgrade_flow.png)

## 4. Sonic-platform-common support for bmc

### 4.1 BMC Redfish client (OpenBMC only)

The `redfish_client.py` module provides the `RedfishClient` class, which facilitates BMC access via cURL requests to Redfish APIs. This class serves as a cURL wrapper for executing various Redfish commands. The class utilizes callback functions to obtain user credentials securely and supports asynchronous task monitoring to handle long-running operations like firmware updates and log dump.

Used when `DEVICE_METADATA|bmc.os` is `openbmc`.

Key functionalities:
1.	Session Management: Handles login and logout operations, ensuring secure sessions with the BMC. It manages tokens and session IDs, and automates re-login if tokens expire.
2.	Firmware Management: Supports listing, updating, and querying firmware versions using Redfish APIs.
3.	BMC Operations: Enables BMC reset requests, password changes, and triggering/debugging log dumps.
4.	Error Handling: Maps cURL error codes to RedfishClient error codes, and includes comprehensive error handling and logging.
5.	Security: Obfuscates sensitive information such as tokens and passwords in logs and command outputs.

### 4.2 BMC Redis client (SONiC BMC only)

When the BMC runs SONiC OS, the Switch-Host does not use Redfish. Instead, `bmc_base.py` connects to the BMC Redis instance over the host–BMC link.

Implementation reference: `sonic_py_common.daemon_base.db_connect_remote()` (same pattern as `thermalctld` mirroring thermals to the BMC).

### 4.3 BMC API scope

**APIs inherited from Device Base** — both BMC OS types where applicable:

| API | OpenBMC | SONiC BMC |
|-----|---------|-----------|
| `get_name()` | Yes | Yes |
| `get_presence()` | Yes | Yes |
| `get_model()` | Yes | Yes |
| `get_serial()` | Yes | Yes |
| `get_revision()` | Yes | Yes |
| `get_status()` | Yes | Yes |
| `is_replaceable()` | Yes | Yes |

**BMC general APIs:**

Return dictionary to show the eeprom info or exception with the failure reason 
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

### 4.4 BMC API details

| API | OpenBMC | SONiC BMC | Notes |
|-----|---------|-----------|-------|
| `get_eeprom()` | Yes | Yes | OpenBMC: Redfish dict (`Manufacturer`, `Model`, `PartNumber`, `PowerState`, `SerialNumber`). SONiC BMC: from `EEPROM_INFO`. Returns `{}` on failure. |
| `get_version()` | Yes | **No** | Redfish firmware query only |
| `reset_root_password()` | Yes | **No** | Redfish only |
| `trigger_bmc_debug_log_dump()` | Yes | **No** | Redfish only |
| `get_bmc_debug_log_dump()` | Yes | **No** | Redfish only |
| `update_firmware(fw_image)` | Yes | **No** | Redfish only |

## 5. CLI commands

### 5.1 BMC OS selection

The Switch-Host stores the configured BMC operating system in CONFIG_DB:

- **Table/key**: `DEVICE_METADATA|bmc`
- **Field**: `os`
- **Values**: `openbmc` | `sonic`
- **Default**: `sonic`

YANG: `leaf os` under `container bmc` in `sonic-device_metadata.yang`.

Runtime API: `sonic_py_common.device_info.get_bmc_os()`.

```
show platform bmc os
---------------------------
sonic

config bmc os sonic
config bmc os openbmc
```

`config bmc os` writes `DEVICE_METADATA|bmc.os`. Subsequent BMC CLI/API calls on the Switch-Host use Redfish or Redis according to this setting.

### 5.2 Platform BMC CLIs

```
show platform bmc summary          # OpenBMC and SONiC BMC (FirmwareVersion is N/A since it cannot be retrieved without Redfish)
---------------------------
Manufacturer: XXXXX
Model: XXXXX
PartNumber: XXXXX
SerialNumber: XXXXX
PowerState: XXXXX
FirmwareVersion: N/A               

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

show platform bmc eeprom            # OpenBMC and SONiC BMC
---------------------------
Manufacturer: XXXXX
Model: XXXXX
PartNumber: XXXXX
PowerState: XXXXX
SerialNumber: XXXXX

config platform firmware install chassis component BMC fw -y ${BMC_IMAGE}   # OpenBMC only

```

## 6. show techsupport

### OpenBMC (Switch-Host techsupport)

On Switch-Host, BMC dump collection via Redfish is **OpenBMC only**. `generate_dump` calls `is_bmc_supported()`, which requires Switch-Host, `bmc.json`, and `get_bmc_os() == openbmc`. When the BMC runs SONiC OS, host-side BMC dump collection is skipped.

For SONiC BMC, collect diagnostics by running `show techsupport` **on the BMC** (local SONiC instance), not from the Switch-Host Redfish path.

`trigger_bmc_debug_log_dump()` and `get_bmc_debug_log_dump()` are called by the generate-dump script on the Switch-Host for OpenBMC only.

### 6.1. Overview
The Switch-Host `show techsupport` command is extended to collect BMC dump logs via Redfish API when the BMC OS is OpenBMC.
This integration is non-blocking and asynchronous: 
It triggers a BMC dump task at the start of the script, then continues with regular 
system data collection. Before the script finishes, it collects the dump from BMC 
using the task ID previously received. 
The design ensures that BMC issues (timeouts, failures, unsupported platforms) 
do not block or interrupt the standard dump flow. 

### 6.2 High-Level Diagram
![show techsupport flow](https://github.com/sonic-net/SONiC/blob/30d7b3524e1e1f25abb4679f7ffa777eabe9f499/images/bmc/show_techsupport_flow.png)

### 6.3 Errors Handling: 
- `generate_dump` checks whether BMC Redfish dump is supported: Switch-Host, `bmc.json` present, and `get_bmc_os() == openbmc`. If not, host-side BMC dump logic is skipped.
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
