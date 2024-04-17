# SONiC Storage Monitoring Daemon Design #
### Rev 0.1 ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Ashwin Srinivasan  | Initial version                   |

## 1. Overview

This document is intended to provide a high-level design for a Storage monitoring daemon.

Solid-State storage devices that use NAND-flash technology to store data offer the end user significant benefits compared to HDDs. Some advantages are reliability, reduced size, increased energy efficiency and improved IO speeds which translates to faster boot times, quicker computational capabilities and an improved system responsiveness overall. Like all devices, however, they experience performance degradation over time on account of a variety of factors such as overall disk writes, bad-blocks management, lack of free space, sub-optimal operational temperature and good-old wear-and-tear which speaks to the overall health of the disk. 

The goal of the Storage Monitoring Daemon (storagemond) is to provide meaningful metrics for the aforementioned issues and enable streaming telemetry for these attributes so that preventative measures may be triggered in the eventuality of performance degradation.

## 2. Data Collection

We are interested in the following characteristics that describe various aspects of the disk:

### **2.1 Dynamic Attributes** 

**The following attributes are updated frequently and describe the current state of the disk**

- File System IO Reads
- File System IO Writes
- Disk IO Reads
- Disk IO Writes
- Reserved Blocks Count
- Temperature
- Firmware
- Health

**Filesystem IO Reads/Writes** - Parsed from the `/proc/diskstats` file, these values correspond to the number of reads and writes successfully carried out in the disk. These values would reset upon reboot.

**Disk IO Reads/Writes** - These fields account for write-amplification and wear-leveling algorithms, and are persistent across reboots and powercycles.

**Reserved Blocks Count** - Reserved blocks are managed by the drive's firmware, and their specific allocation and management may vary between disk manufacturers. The primary purposes of reserved blocks in a disk are:

- **Bad-block replacement:** When the firmware detects a bad block, it can map it to a reserved block and continue using the drive without data loss.
- **Wear Leveling:** Reserved blocks are used to replace or relocate data from cells that have been heavily used, ensuring that all cells are used evenly. 
- **Over-Provisioning:** Over-provisioning helps maintain consistent performance and extends the lifespan of the disk by providing additional resources for wear leveling and bad block management.
- **Garbage collection:** When files are deleted or modified, the old data needs to be erased and marked as available for new data. Reserved blocks can help facilitate this process by providing a temporary location to move valid data from blocks that need to be erased. 

- **Temperature, Firmware, Health** - These fields are self-explanatory

### **2.2 Static Attributes**

**These attributes provide informational context about the Storage disk**

- **Vendor Model**
- **Serial Number**

These fields are self-explanatory.


### **2.3 `storagemond` Daemon Flow**

1. The "storagemond" process will be initiated by the "pmon" Docker container.

2. As part of initialization process, the daemon will query the Config DB for an entry called `polling_interval` within a newly proposed table `STORAGEMOND_CONFIG` and use the value to set the looping frequency for getting dynamic informaton. In the absense of this table or entry, we would default to 3600 seconds.

3. After initialization, the daemon will gather static information utilizing S.M.A.R.T capabilities through instantiated class objects such as SsdUtil and EmmcUtil. This information will be subsequently updated in the StateDB.

4. The daemon will parse dynamic attributes also utilizing S.M.A.R.T capabilities via the corresponding class member functions, and update the StateDB per the preset frequency.

**NOTE:** The design requires a concurrent PR wherein EmmcUtil, SsdUtil classes are enhanced to gather Disk and FS IO Read/Write stats and Reserved Blocks information as detailed in section [2.4.1 below](#241-ssdbase-api-additions).

This is detailed in the sequence diagram below:

![image.png](images/storagemond_SequenceDiagram.png)

### **2.4 Data Collection Logic**

The SONiC OS currently includes logic for parsing storage disk information from various vendors through the `EmmcUtil` and `SsdUtil` classes, facilitated by base class definitions provided by `SsdBase`. We utilize this framework to collect the following details:

- **Static Information**: Vendor Model, Serial Number
- **Dynamic Information**: Firmware, Temperature, Health

The following section will therefore only go into detail about data collection of attributes mentioned in [section 2.1](#21-dynamic-attributes).


#### **2.4.1 SsdBase API additions**

In order to parse Disk IO reads/writes and Number of Reserved Blocks, we would need to add the following member methods to the `SsdBase` class in [ssd_base.py](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_ssd/ssd_base.py) and provide a generic implementation in [ssd_generic.py](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_ssd/ssd_generic.py):


```
class SsdBase(object):

...

def get_disk_io_reads(self):
"""
Retrieves the total number of Input/Output (I/O) reads done on an SSD

Returns:
    An integer value of the total number of I/O reads
"""

def get_disk_io_writes(self):
"""
Retrieves the total number of Input/Output (I/O) writes done on an SSD

Returns:
    An integer value of the total number of I/O writes
"""

def get_reserved_blocks(self):
"""
Retrieves the total number of reserved blocks in an SSD

Returns:
    An integer value of the total number of reserved blocks
"""

```

#### **2.4.2 Support for Multiple Storage Disks**

In order to get a clear picture of the number of disks and type of each disk present on a device, we introduce a new class `StorageDevices()`. This proposed class will reside in the `src/sonic-platform-common/sonic_platform_base/sonic_ssd` directory, within the file named `storage_devices.py`. This new class provides the following methods:

```
class StorageDevices():

# A dictionary where the key is the name of the disk and the value is the corresponding class object
devices = {}

...

def get_storage_devices(self):
"""
Retrieves all the storage disks on the device and adds their names as key to the 'devices' dict.

"""

def get_storage_device_object(self):
"""
Instantiates an object of the corresponding storage device class:

'ata'       - SsdUtil   - Full support
'usb'       - UsbUtil*  - Not currently supported
'mmcblk'    - EmmcUtil* - Limited Support

Adds the instantiated class object as a value to the corresponding key in the dictionary object.

*NOTE: SsdUtil is supported currently. Limited support for EmmcUtil. Future support planned for USBUtil and NVMeUtil

"""
```

This class is a helper to the Storage Daemon class.

**get_storage_devices() Logic:**

- In the base path of `/sys/block/`, for each fd:
    - If the fd does not have `boot` or `loop`, add it as a key to the `devices` dictionary with a temporary value of `NoneType`
    ```
    Example:
    admin@sonic:/sys/block$ ls | grep -v -e "boot" -e "loop"
    mmcblk0
    sda
    ```

In the example scenario above, the dictionary `devices` would look like this:

```
devices = {
'mmcblk0' : None
'sda'     : None
}
```

**get_storage_device_object() Logic:**

- For each key in the `devices` dictionary:
    - If key starts with the term `sd`:
        - If the realpath of `/sys/block/[KEY]/device` has the term `ata` in it:
        - Instantiate an object<sup>READ NOTE</sup> of type `SsdUtil` and add this object as value of the key
        ```
        Example:
        root@str-msn2700-02:~# cd /sys/block/sda/../../../0:0:0:0
        root@str-msn2700-02:/sys/devices/pci0000:00/0000:00:1f.2/ata1/host0/target0:0:0/0:0:0:0#
        ```
    - else if the realpath of `/sys/block/[KEY]/device` has the term `usb` in it:
        - Instantiate an object<sup>READ NOTE</sup> of type `UsbUtil` and add this object as value of the key
        ```
        Example:
        root@str2-7050qx-32s-acs-01:~# cd /sys/block/sda/../../../2:0:0:0
        root@str2-7050qx-32s-acs-01:/sys/devices/pci0000:00/0000:00:12.2/usb1/1-2/1-2:1.0/host2/target2:0:0/2:0:0:0#
        ```
- else if key starts with the term `mmcblk`:
    - Instantiate an object<sup>READ NOTE</sup> of type `EmmcUtil` and add this object as value of the key
    ```
    Example:
    root@sonic:/sys/block$ ls | grep -i "mmcblk" | grep -v "boot" | grep -v "loop"
    mmcblk0
    ```

**Example usage:**

Assuming a device contains the following storage disks:
```
root@str-a7280cr3-2:~# ls /sys/block/
loop0  loop1  loop2  loop3  loop4  loop5  loop6  loop7  **mmcblk0**  mmcblk0boot0  mmcblk0boot1  **sda**
```

We would instantiate an object of the StorageDevices() class
`storage = StorageDevices()`

`storage.devices` would contain:
```
{
    'mmcblk0': <Emmcutil object>,
    'sda': <SsdUtil object>
}
```

we would then get static and dynamic information by leveraging the respective member function implementations of `SsdUtil` and `EmmcUtil`, as they both derive from `SsdBase`.
We then leverage the following proposed StateDB schema to store and stream information about each of these disks.


**NOTE:** <br>
**Full support** -- monitors all the attributes mentioned in [section 2](#2-data-collection)<br>
**Limited support** -- Support unavailable for Dynamic fields mentioned in [section 2.1](#21-priority-0-attributes)<br>
**Not currently supported** -- Class currently unimplemented, no object created. No monitoring currently available.<br>

<sub>UsbUtil and NVMeUtil classes are not yet available. EmmcUtil class does not currently support disk IO reads, disk IO writes and Reserved Blocks.</sub>

#### **2.4.3 Support for common implementations**

Specific data, such as Filesystem Input/Output (FS IO) Reads/Writes, can be uniformly collected regardless of the storage disk type, as it is extracted from files generated by the Linux Kernel. To streamline the process of gathering this information, we propose the implementation of a new parent class `StorageCommon()`, from which classes such as SsdUtil, EmmcUtil, USBUtil, and NVMUtil would inherit in addition to `SsdBase` (to be renamed `StorageBase`). This proposed class will reside in the `src/sonic-platform-common/sonic_platform_base/sonic_ssd` directory, in `storage_common.py`. The `StorageCommon()` class will have the following functions:

```
def _parse_fsstats_file(self):
    """
    Function to parse a file containing the previous latest FS IO Reads/Writes values from a file (more on this in the subsequent section) and saves it to member variables

    Args: None
    
    Returns: None

def get_fs_io_reads(self):
    """
    Function to get the total number of reads on each disk by parsing the /proc/diskstats file

    Returns:
        The total number of FSIO reads
    
    Args:
        N/A
    """

def get_fs_io_writes(self):
    """
    Function to get the total number of writes on each disk by parsing the /proc/diskstats file

    Returns:
        The total number of FSIO writes
    
    Args:
        N/A
    """
```
**Accounting for reboots and unintended powercycles**

The reset of values in `/proc/diskstats` upon device reboot or power cycle presents a challenge for maintaining long-term data integrity. To mitigate this challenge, we propose the following design considerations:

1. Introduction of a bind-mounted directory within the pmon container at `/usr/share/storagemon/` which maps to `/host/pmon/storagemon/` on the host:
    - This directory hosts a file named `fsio-rw-stats.json`, where the latest filesystem Reads/Writes values are saved.
    - This file would be read by the daemon on initialization after a planned reboot of the system, or in a graceful `stormond` restart scenario.

2. Implementation of a script, tentatively named `parse-fsio-rw-stats.py`, to be invoked by SONiC's reboot utility:
    - This script would live in [sonic-utilities](https://github.com/sonic-net/sonic-utilities/tree/master/scripts) and would be called by the reboot script
    - This script will be responsible for parsing and storing the most recent FS IO reads and writes from the `fs-rw-stats.json` file.
    - These values would be stored in the `/host/pmon/storagemon/fsio-rw-stats.json` file(s).


**Daemon Restart / Reboot / Unintended Powercycle Scenario Behaviors**

1. **Planned cold, fast and warm reboot scenario**
    - Just before OS level reboot is called, we save the latest FSIO Reads and Writes from `/proc/diskstats` file to the `fsio-rw-stats.json` file by calling the `parse-fsio-rw-stats.py` script from the corresponding cold/fast/warm-reboot script.
    - On reboot, the number of reads/writes as parsed from the `fsio-rw-stats.json` file would be greater than the latest value from `/proc/diskstats`. In this scenario, we consider the RW values from `fsio-rw-stats.json` as initial values and would add the latest RW values from `/proc/diskstats` file to them each time before writing to the database.

2. **stormond graceful restart and crash scenario**
    - A **pidfile** created by stormond upon initialization in the `/var/tmp` directory would help determine if `stormond` crashed or was gracefully shutdown.
    - In either scenario, since the system did **not** reboot, the filesystem reads/writes would not be reset in the `/proc/diskstats` file. 
    - Therefore, when `stormond` restarts, we simply overwrite the pidlfile with the new PID of the daemon and carry on with normal functionality.

3. **System unintended powercycle scenario**
    - In this scenario, reads and writes counts in `/proc/diskstats` file is reset.
    - Secondly, we would not have had a chance to save the latest RW counts to the `fsio-rw-stats.json` file.
    - Thirdly, the pidfile would also be cleared and there would truly be no way to tell if this was a planned or unplanned powercycle.
    - Therefore, this is the only scenario where there exists a possibility of drift between the measured FSIO RW and actual RW. This is a concession we are willing to make.

**Logic for StorageCommon() get_fs_io_reads and get_fs_io_writes functions:**

These two functions, `get_fs_io_reads` and `get_fs_io_writes`, are designed to retrieve the total number of disk reads and writes, respectively, by parsing the `/proc/diskstats` file. They utilize similar logic, differing only in the column index used to extract the relevant information.

1. **Check for `psutil` Module**:
   - The functions first check if the `psutil` module is available in the current environment by examining the `sys.modules` dictionary.

2. **Use `psutil` Module (if available)**:
   - If `psutil` is available:
     - The functions retrieve disk I/O counters, specifying the disk for which to get the counters.
     - They then get the read or write count for the specified disk using `read_count` or `write_count` respectively.

3. **Fallback to Parsing Disk Stats File**:
   - If `psutil` is not available:
     - The functions open the `/proc/diskstats` file
     - They read the contents of the file and iterate over each line.
     - For each line, they check if the name of the storage disk is present.
     - If the name of the storage disk is found in the line, they return the value at the appropriate zero-based index (3 for reads, 7 for writes).
     - If no line contains the name of the storage disk, they save the respective values as 0.

4. **Combine the initial Reads/Writes with the current values as needed**:
     - First they determine whether there is a need to combine the current RW values with the initial RW values.
     - In a planned reboot or graceful restart scenario, they add the current and new reads and writes, respectively, to get the latest count
     - In an unplanned `stormond` crash scenario, they do NOT add the initial RW values with the newly parsed values.
     - These values are then returned to the caller to be written to `STATE_DB`.


#### **2.4.4 storagemond Class Diagram**

![image.png](images/StoragemonDaemonClassDiagram.png)

## **3. Schema Changes**

### **3.1 StateDB Schema**
```
; Defines information for each Storage Disk in a device

key                 = STORAGE_INFO|<disk_name>  ; This key is for information about a specific storage disk - STORAGE_INFO|SDX

; field             = value

device_model        = STRING                    ; Describes the Vendor information of the disk                                           (Static)
serial              = STRING                    ; Describes the Serial number of the disk                                                (Static)
temperature_celsius = STRING                    ; Describes the operating temperature of the disk in Celsius                             (Dynamic)
fs_io_reads         = STRING                    ; Describes the total number of filesystem reads completed successfully                  (Dynamic)
fs_io_writes        = STRING                    ; Describes the total number of filesystem writes completed successfully                 (Dynamic)
disk_io_reads       = STRING                    ; Describes the total number of reads completed successfully from the SSD (Bytes)        (Dynamic)
disk_io_writes      = STRING                    ; Describes the total number of writes completed on the SSD (Bytes)                      (Dynamic)
reserved_blocks     = STRING                    ; Describes the reserved blocks count of the SSD                                         (Dynamic)
firmware            = STRING                    ; Describes the Firmware version of the SSD                                              (Dynamic)
health              = STRING                    ; Describes the overall health of the SSD as a % value based on several SMART attrs      (Dynamic)
```

NOTE: disk_io_reads and disk_io_writes return total LBAs read/written. 'LBA' stands for Logical Block Address. 
To get the raw value in bytes, we multiply thr num. LBAs by the disk's logical block address size (typically 512 bytes).<br>

Example: For an SSD with name 'sda', the STATE_DB entry would be:

```
root@sonic:~# docker exec -it database bash
root@sonic:/# redis-cli -n 6
127.0.0.1:6379[6]> keys STORAGE*
1) "STORAGE_INFO|mmcblk0"
2) "STORAGE_INFO|sda"
127.0.0.1:6379[6]>
127.0.0.1:6379[6]> hgetall STORAGE_INFO|sda
 1) "device_model"
 2) "SATA SSD"
 3) "serial"
 4) "SPG2043056Z"
 5) "firmware"
 6) "FW1241"
 7) "health"
 8) "N/A"
 9) "temperature"
10) "30"
11) "fs_io_reads"
12) "28753"
13) "fs_io_writes"
14) "92603"
15) "disk_io_reads"
16) "15388141951"
17) "disk_io_writes"
18) "46070618960"
19) "reserved_blocks"
20) "32"

```

### **3.2 ConfigDB Schema**
```
; Defines information for each Storage Disk in a device

key                 = STORAGEMOND_CONFIG|  ; This key is for information about a specific storage disk - STORAGE_INFO|SDX

; field             = value

polling_interval    = STRING               ; The polling frequency for reading dynamic information
```

## Future Work

1. Full support for eMMC
2. Support for USB and NVMe storage disks
3. Refactor `ssdutil` [in sonic-utilities](https://github.com/sonic-net/sonic-utilities/tree/master/ssdutil) to cover all storage types, including changing the name of the utility to 'storageutil'

<br><br><br>
<sup>[Back to top](#1-overview)</sup>
