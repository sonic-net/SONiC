# SONiC SSD Daemon Design #
### Rev 0.1 ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Ashwin Srinivasan  | Initial version                   |

## 1. Overview

This document is intended to provide a high-level design for a Solid-State Drive monitoring daemon.

Solid-State Drives (SSDs) are storage devices that use NAND-flash technology to store data. They offer the end user significant benefits compared to HDDs, some of which include reliability, reduced size, increased energy efficiency and improved IO speeds which translates to faster boot times, quicker computational capabilities and an improved system responsiveness overall. Like all devices, however, they experience performance degradation over time on account of a variety of factors such as overall disk writes, bad-blocks management, lack of free space, sub-optimal operational temperature and good-old wear-and-tear which speaks to the overall health of the SSD. 

The goal of the SSD Monitoring Daemon (ssdmond) is to provide meaningful metrics for the aforementioned issues and enable streaming telemetry for these attributes so that the required preventative measures are triggered in the eventuality of performance degradation.

## 2. Data Collection

We are intrested in the following characteristics that describe various aspects of the SSD:

### **2.1 Priority 0 Attributes** 

**The following are dynamic fields, offering up-to-date information that describes the current state of the SSD**

    - IO Reads
    - IO Writes
    - Reserved Blocks Count
    - Temperature

**IO Reads/Writes** - SSDs use wear-leveling algorithms to distribute write and erase cycles evenly across the NAND cells to extend their lifespan. However, write amplification can occur when data is written, rewritten, and erased in a way that creates additional write operations, which can slow down performance.

**Reserved Blocks Count** - Reserved blocks in a Solid State Drive (SSD) serve several critical purposes to enhance the drive's performance, reliability, and longevity. These reserved blocks are managed by the drive's firmware, and their specific allocation and management may vary between SSD manufacturers. The primary purposes of reserved blocks in an SSD are:

- **Bad-block replacement:** When the firmware detects a bad block, it can map it to a reserved block and continue using the drive without data loss.
- **Wear Leveling:** Reserved blocks are used to replace or relocate data from cells that have been heavily used, ensuring that all cells are used evenly. 
- **Over-Provisioning:** Over-provisioning helps maintain consistent performance and extends the lifespan of the SSD by providing additional resources for wear leveling and bad block management.
- **Garbage collection:** When files are deleted or modified, the old data needs to be erased and marked as available for new data. Reserved blocks can help facilitate this process by providing a temporary location to move valid data from blocks that need to be erased. 

**Temperature** - Extreme temperatures can affect SSD performance. Excessive heat can lead to throttling to prevent damage, while extreme cold can slow down data access.


### **2.2 Priority 1 Attributes**

**These are a combination of static (S) and dynamic (D) fields, offering secondary information that provides additional context about the SSD**

    - Vendor Model (S)
    - Serial Number (S)
    - Firmware (S)
    - Health (D)

These fields are self-explanatory.


### **2.3 `ssdmond` Daemon Flow**

0. SONiC partners would be responsible for configuring the **loop timeout** - This determines how often the dynamic information would be updated. Default is 6 hours.

1. `ssdmond` would be started by the `pmon` docker container
2. The daemon would gather the static info once init-ed, by leveraging the `SsdBase` class and update the StateDB
3. It would periodically parse the priority 0 attributes by leveraging `SsdBase` class and update the StateDB.

This is detailed in the sequence diagram below:

![image.png](images/SSDMOND_SequenceDiagram.png)

### **2.4 Data Collection Logic**

The SONiC OS already contains logic to parse information about SSDs from several vendors by way of the `ssdutil` platform utility. We leverage this utility to gather the following information:

- Priority 0: Temperature
- Priority 1: All aforementioned attributes

This section will therefore only go into detail about data collection of attributes mentioned in [section 2.1](#21-priority-0-attributes).

#### **2.4.1 SsdBase API additions**

In order to collect IO reads/writes and number of reserved blocks, we would need to add the following member methods to the `SsdBase` class in [ssd_base.py](https://github.com/sonic-net/sonic-platform-common/blob/master/sonic_platform_base/sonic_ssd/ssd_base.py):


```
class SsdBase(object):

...

def get_io_reads(self):
"""
Retrieves the total number of Input/Output (I/O) reads done on an SSD

Returns:
    An integer value of the total number of I/O reads
"""

def get_io_writes(self):
"""
Retrieves the total number of Input/Output (I/O) writes done on an SSD

Returns:
    An integer value of the total number of I/O writes
"""

def get_reserves_blocks(self):
"""
Retrieves the total number of reserved blocks in an SSD

Returns:
    An integer value of the total number of reserved blocks
"""

```

#### **2.4.2 Support for Multiple SSDs**

The `ssdutil` utility assumes that the SSD drive is  `/dev/sda` whereas the drive letter could be any label based on the nuber of SSDs. We leverage the `lsblk` command to get  list of all the SSDs in the device. For instance, if there were three disks labeled 'sda', 'sdb', and 'sdc' on a device, the output of the `lsblk -d -o name,type` command would typically look something like this:

NAME TYPE
sda  disk
sdb  disk
sdc  disk

This output lists the names of the disks (sda, sdb, and sdc) and their types (which are "disk" in this case, indicating that they are block storage devices). This output format makes it easy to identify the disks on any system. We then leverage the following proposed StateDB schema to store and stream information about each of these disks.

## **3. StateDB Schema**
```
; Defines information for each SSD in a device

key                 = SSD_INFO|<ssd_name>               ; This key is for information that does not change for the lifetime of the SSD - SSD_INFO|SDX

; field             = value

temperature_celsius = STRING                            ; Describes the operating temperature of the SSD in Celsius                             (Priority 0, Dynamic)
io_reads            = INT                               ; Describes the total number of reads completed successfully from the SSD               (Priority 0, Dynamic)
io_writes           = INT                               ; Describes the total number of writes completed on the SSD                             (Priority 0, Dynamic)
reserve_blocks      = INT                               ; Describes the reserved blocks count of the SSD                                        (Priority 0, Dynamic)
device_model        = STRING                            ; Describes the Vendor information of the SSD                                           (Priority 1, Static)
serial              = STRING                            ; Describes the Serial number of the SSD                                                (Priority 1, Static)
firmware            = STRING                            ; Describes the Firmware version of the SSD                                             (Priority 1, Static)
health              = STRING                            ; Describes the overall health of the SSD as a % value based on several SMART attrs     (Priority 1, Dynamic)
```

Example: For an SSD with name 'SDA', the STATE_DB entry would be:

```
127.0.0.1:6379[6]> KEYS SSD_INFO|*
1) "SSD_INFO|SDB"
2) "SSD_INFO|SDA"
127.0.0.1:6379[6]> HGETALL SSD_INFO|SDA
 1) "temperature"
 2) "30C"
 3) "io_reads"
 4) "49527"
 5) "io_writes"
 6) "238309"
 7) "reserve_blocks"
 8) "0"
 9) "device_model"
10) "InnoDisk Corp. - mSATA 3IE3"
11) "health"
12) "92"
13) "serial"
14) "BCA11712190600251"
15) "firmware"
16) "S16425cG"
127.0.0.1:6379[6]> 
```

## Future Work

1. Support for eMMC storage
2. Support for more SSD vendors

## References

### 1. [man tune2fs](https://linux.die.net/man/8/tune2f)
### 2. [kernel.org /proc/diskstats](https://www.kernel.org/doc/Documentation/ABI/testing/procfs-diskstats)

<br><br><br>
<sup>[Back to top](#1-overview)</sup>