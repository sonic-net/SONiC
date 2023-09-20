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

**Reserved Blocks Count** - Reserving some number of filesystem blocks for use by privileged processes is done to avoid filesystem fragmentation, and to allow system daemons, such as syslogd(8), to continue to function correctly after non-privileged processes are prevented from writing to the filesystem. Normally, the default percentage of reserved blocks is 5%.<sup>[1](#1-man-tune2fs)</sup>

**Temperature** - Extreme temperatures can affect SSD performance. Excessive heat can lead to throttling to prevent damage, while extreme cold can slow down data access.


### **2.2 Priority 1 Attributes**

**These are a combination of static (S) and dynamic (D) fields, offering secondary information that provides additional context about the SSD**

    - Vendor Model (S)
    - Serial Number (S)
    - Firmware (S)
    - Health (D)

These fields are self-explanatory.


### **2.3 `ssdmond` Daemon Flow**

0. Vendor would be responsible for configuring the following values:
    - **loop timeout** - This determines how often the dynamic information would be updated. Default is 6 hours.
    - **SSD vendor-specific search terms** - This would ensure that all the attributes are properly parsed from the device.

1. `ssdmond` would be started by the `pmon` docker container
2. The daemon would gather the static info once init-ed, by leveraging the `ssdutil` utility and update the StateDB
3. It would periodically parse the priority 0 attributes either by leveraging `ssdutil` or directly through Linux utilities and update the StateDB.

This is detailed in the sequence diagram below:

![image.png](images/SSDMOND_SequenceDiagram.png)


NOTE: While it is previously established that we use the abstraction provided by the `ssdutil` class to offer vendors the opportunity to implement their own SSD parsing logic, the [primary intent](#1-overview) of this iteration of the design is to enable streaming telemetry of these attributes, i.e., update the StateDB with the parsed data. A design choice is therefore made to bypass the abstraction logic in favor of this goal in the interim, with the expressed understanding that said abstraction will follow in a [future version](#future-work) of this daemon.


### **2.4 Data Collection Logic**

The SONiC OS already contains logic to parse information about SSDs from several vendors by way of the `ssdutil` platform utility. We leverage this utility to gather the following information:

- Priority 0: Temperature
- Priority 1: All aforementioned attributes

This section will therefore only go into detail about data collection of attributes mentioned in [section 2.1](#21-priority-0-attributes):

#### **2.4.1 IO Reads/Writes**

- grep `/proc/diskstats` for statistics about the SSD of interest
- Read the 4th value for reads completed successfully and the 8th value for writes completed<sup>[2](#2-kernelorg-procdiskstats)</sup>

#### **2.4.2 Reserved Blocks Count**

- Examine the SMART data for attributes related to reserved blocks or over-provisioning.
- The exact attribute name and number can vary depending on the SSD manufacturer and model.
- Look for keywords like "Reserved Block Count," "Over Provisioning," or similar terms.

    Here's an example of what the SMART data output might look like:

    ```
    ...
    ID# ATTRIBUTE_NAME          FLAGS    VALUE WORST THRESH FAIL RAW_VALUE
    ...
    173 Wear_Leveling_Count     0x0032   100   100   000    Old_age   Always       -       123
    192 Power-Off_Retract_Count 0x0032   100   100   000    Old_age   Always       -       456
    ...

    ```

    In this example, the "Wear_Leveling_Count" attribute might be indicative of reserved blocks or over-provisioning. However, the specific attribute and its interpretation can vary, so we make the search term and ID configurable by our vendors while maintaining a default search term in the event that this value is left unconfigured.

## **StateDB Schema**
```
; Defines information for the SSD in a device

key                 = SSD_INFO                       ; This key is for information that does not change for the lifetime of the SSD

; field              = value

Temperature         = STRING                            ; Describes the operating temperature of the SSD                                        (Priority 0, Dynamic)
io_reads            = INT                               ; Describes the total number of reads completed successfully from the SSD               (Priority 0, Dynamic)
io_writes           = INT                               ; Describes the total number of writes completed on the SSD                             (Priority 0, Dynamic)
reserve_blocks      = INT                               ; Describes the reserved blocks count of the SSD                                        (Priority 0, Dynamic)
device_model        = STRING                            ; Describes the Vendor information of the SSD                                           (Priority 1, Static)
serial              = STRING                            ; Describes the Serial number of the SSD                                                (Priority 1, Static)
firmware            = STRING                            ; Describes the Firmware version of the SSD                                             (Priority 1, Static)
health              = STRING                            ; Describes the overall health of the SSD                                               (Priority 1, Dynamic)
```

## Future Work

1. Code abstraction and CLI support for aforementioned newly introduced fields
2. Support for eMMC storage

## References

### 1. [man tune2fs](https://linux.die.net/man/8/tune2f)
### 2. [kernel.org /proc/diskstats](https://www.kernel.org/doc/Documentation/ABI/testing/procfs-diskstats)

<br><br><br>
<sup>[Back to top](#1-overview)</sup>