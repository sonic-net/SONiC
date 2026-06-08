# System Resource Monitoring

## Table of Contents

- [1.Revision](#1-revision)
- [2.Scope](#2-scope)
- [3. Definitions/Abbreviations](#3-definitionsabbreviations)
- [4. Feature Overview](#4-feature-overview)
- [5. Requirements](#5-requirements)
    - [5.1 Functional Requirements](#51-functional-requirements)
    - [5.2 Functional Description](#52-functional-description)
      - [5.2.1 CPU Utilization Monitoring](#521-cpu-utilization-monitoring)
      - [5.2.2 Memory Utilization Monitoring](#522-memory-utilization-monitoring)
      - [5.2.3 Storage/Disk Utilization Monitoring](#523-storagedisk-utilization-monitoring)
      - [5.2.4 Threshold-Based Alarming](#526-threshold-based-alarming)
      - [5.2.5 Syslog Notifications](#527-syslog-notifications)
    - [5.3 Target Deployment Use Cases](#53-target-deployment-use-cases)
    - [5.4 Scalability Requirements](#54-scalability-requirements)
      - [5.4.1 Redis Memory Footprint Estimation](#541-config-dbRedis-memory-footprint-estimation)
      - [5.4.2 CPU Overhead](#542-cpu-overhead)
- [6. Architecture Design](#6-architecture-design)
    - [6.1 Basic Approach ](#61-basic-approach)
    - [6.2 Container ](#62-container)
- [7. High-Level Design](#7-high-level-design)
    - [7.1 Overview](#71-design-overview)
    - [7.2 DB Schema](#72-db-schema)
      - [7.2.1 CONFIG_DB](#721-config_db)
      - [7.2.2 STATE_DB](#722-state_db)
      - [7.2.3 COUNTERS_DB](#723-counters_db)
    - [7.3 Flow Diagrams](#73-flow-diagrams)
      - [7.3.1 Resource Collection Flow](#731-resource-collection-flow)
      - [7.3.2 Threshold Alarm Flow](#732-threshold-alarm-flow)
    - [7.4 Sequence Diagram](#74-sequence-diagrams)
- [8. SAI API](#8-sai-api)
    - [8.1 Platform API Integration](#81-platform-api-integration)
- [9. Configuration and Management](#9-configuration-and-management)
    - [9.1 Daemon Design](#91-daemon-design)
      - [9.1.1 system-resource-monitord](#911-system-resource-monitord)
      - [9.1.2 Collection and History Engine](#912-collection-and-history-engine)
      - [9.1.3 Threshold and Alarm Engine](#913-threshold-and-alarm-engine)
    - [9.2 Switch State Service Design](#92-switch-state-service-design)
    - [9.3 SyncD](#93-syncd)
    - [9.4 CLI](#94-cli)
      - [9.4.1 Configuration Commands](#941-configuration-commands)
      - [9.4.2 Show Commands](#942-show-commands)
      - [9.4.3 Clear Commands](#943-clear-commands)
    - [9.5 REST API Support](#95-rest-api-support)
    - [9.6 gNMI Support](#96-gnmi-support)
    - [9.7 YANG Model](#97-yang-model)
    - [9.8 Error Handling](#98-error-handling)
      - [9.8.1 Data Collection Errors](#981-data-collection-errors)
      - [9.8.2 Configuration Errors](#982-configuration-errors)
      - [9.8.3 Platform and Hardware Errors](#983-platform-and-hardware-errors)
      - [9.8.4 Daemon Lifecycle Errors](#984-daemon-lifecycle-errors)
      - [9.8.5 Infrastructure Errors](#985-Infrastructure-errors)
      - [9.8.6 CLI, REST, and gNMI](#986-cli-rest-and-gnmi-errors)
      - [9.8.7 Race Conditions and Concurrency](#987-race-conditions-and-concurrency)
      - [9.8.8 Error Recovery Summary](#988-error-recovery-summary)
      - [9.8.9 Error Code Reference](#989-error-code-reference)
      - [9.8.10 Syslog Error Message Catalog](#9810-syslog-error-message-catalog)
    - [9.9 Serviceability and Debug](#99-serviceability-and-debug)
      - [9.9.1 Logging](#991-logging)
      - [9.9.2 Techsupport Integration](#992-techsupport-integration)
      - [9.9.3 Health Check](#993-health-check)
- [10. Warmboot and Fastboot Design Impact](#10-warmboot-and-fastboot-design-impact)
    - [10.1 Warm Boot Requirements](#101-warm-boot-requirements)
    - [10.2 Warm Boot Support](#102-warm-boot-support)
- [11. Memory Consumption ](#11-Memory-Consumption)
- [12. Restrictions/Limitations](#12-restrictionslimitations) 
- [13. Testing Requirements/Design](#13-testing-requirementsdesign)
    - [13.1 Unit Test Cases](#131-unit-test-cases)
    - [13.2 Functional Test CAses](#132-Fuctional-Test-cases)
    - [13.3 System Test cases](#133-System-Test-cases)
- [14. Open/Action items - if any](#14-openaction-items) 
- [Appendix A: Default Configuration Summary](#appendix-a-default-configuration-summary)
- [Appendix B: init_cfg.json Defaults](#appendix-b-init-cfg-json-defaults)
- [Appendix C: Syslog Message Reference](#appendix-c-syslog-message-reference)
- [Appendix D: Requirements Traceability Matrix](#appendix-d-requirements-traceability-matrix)
- [List of Tables](#list-of-tables)
    - [Table 1: Abbreviations](#3-definitions/abbreviations)
    - [Table 2: CONFIG_DB — SYSTEM_RESOURCE_MONITOR](#721-config_db)
    - [Table 3: CONFIG_DB — SYSTEM_RESOURCE_THRESHOLD](#722-config_db)
    - [Table 4: STATE_DB — CPU, Memory, Storage, Alarm Tables](#722-state_db)

### 1. Revision

| Rev  | Date         | Author                   | Change Description         |
|------|------------  |--------------------------|----------------------------|
| 1.1  | 2026-06-02   | System Resource Team     | Initial version            |

### 2. Scope

This document describes the high-level design of the System Resource Monitoring feature. It covers:

#### 2.1 In Scope                                                                                                      

1. CPU utilization per logical core (current snapshot and history)
2. Physical RAM utilization (current snapshot and history)                     
3. Storage partition utilization for permanently attached devices            
4. Threshold-based alarms for CPU, memory, disk                              
5. Syslog notifications for threshold violation events

#### 2.2 Out of Scope

1. CPU utilization per container / per socket / aggregate  
2. Per-process or per-container memory                     
3. Removable storage (USB), aggregate device utilization, total/used/free space 
4. Minimum threshold alarms                                 
5. SNMP traps (may be added later)                        

### 3. Definitions/Abbreviations

| Term       | Definition                                           |
|----------- |------------------------------------------------------|
| ASIC       | Application-Specific Integrated Circuit              |
| CONFIG_DB  | SONiC configuration database (Redis)                 |
| CPU        | Central Processing Unit                              |
| gNMI       | gRPC Network Management Interface                    |
| HLD        | High Level Design                                    |
| NAND       | Not-AND flash memory                                 |
| OID        | Object Identifier                                    |
| RAM        | Random Access Memory                                 |
| REST       | Representational State Transfer                      |
| SAI        | Switch Abstraction Interface                         |
| SNMP       | Simple Network Management Protocol                   |
| SSD        | Solid-State Drive                                    |
| STATE_DB   | SONiC state database (Redis)                         |
| YANG       | Yet Another Next Generation (data modeling language) |

---

### 4. Feature Overview

This document provides a high-level design for the System Resource Monitoring (SRM) feature in SONiC, enabling proactive system health management and prevent resource exhaustion. It covers CPU, memory, and storage utilization monitoring with history and threshold-based alarming; and syslog-based notifications. The document is written so that a new engineer or architect joining the SONiC community can understand the end-to-end feature design.

### 5 Requirements

#### 5.1 Functional Requirements

| ID    | Requirement Summary                                                                                                         |
|-------|-----------------------------------------------------------------------------------------------------------------------------|
| FR-1  | Retrieve current snapshot of CPU utilization **per logical core**.                                                          |
| FR-2  | Retrieve CPU utilization **history per core** for a configurable duration (default 60 min) at a configurable measurement interval (default 5 min). Each value is the average utilization during that interval. History is read-only and non-persistent across restarts. |
| FR-3  | Retrieve current snapshot of system-level physical memory (RAM): available and used.                                        |
| FR-4  | Retrieve memory utilization **history** for a configurable duration (default 60 min) at a configurable measurement interval (default 5 min). History is read-only and non-persistent across restarts.  |
| FR-5  | Retrieve storage partition information and utilization for all permanently attached storage devices. Report number of partitions per device and utilization percentage of each mounted partition. Removable devices excluded. |
| FR-6  | Support configurable maximum CPU utilization threshold (default 85 %). Generate alarm when exceeded; auto-clear when below. |
| FR-7 | Support configurable maximum memory utilization threshold (default 80 %). Generate alarm when exceeded; auto-clear when below.    |
| FR-8 | Support configurable maximum flash/disk utilization threshold (default 75 %). Generate alarm when exceeded; auto-clear when below.    |
| FR-9 | Generate syslog notifications for all threshold violations (raise and clear).                                               |

#### 5.2 Functional Description

##### 5.2.1 CPU Utilization Monitoring

**Current Snapshot (FR-1):**

The daemon retrieves CPU utilization metrics by reading the `/proc/stat` file and computing the utilization percentage for each logical CPU core (e.g., cpu0, cpu1, ..., cpuN). Each core's utilization is calculated and reported independently.

**Calculation Method**

CPU utilization is derived using the following formula:
utilization = 100.0 * (total_delta - idle_delta) / total_delta


Where:
- `idle_delta` = Difference in idle time (in jiffies) between two consecutive reads
- `total_delta` = Difference in total CPU time (in jiffies) between two consecutive reads

**Polling Mechanism**

- **Default Polling Interval:** 5 seconds
- **Rationale:** This interval provides a balance between responsiveness and system overhead
- **Configuration:** The polling interval is fixed at 5 seconds and is not user-configurable. It will be fine-tuned based on benchmarking results that measure CPU cycles consumed during periodic operations

**Implementation Notes**

- Two consecutive reads of `/proc/stat` are required, separated by the fixed polling interval of 5 seconds
- Delta values are computed by subtracting the previous jiffy counters from the current values
- The calculation ensures accurate utilization percentages for each logical core

**History (FR-2):**

The daemon maintains CPU utilization history per logical core using a circular buffer mechanism. Historical data is stored in STATE_DB and is non-persistent (cleared on daemon restart).

The following parameters are configured at the system level and apply uniformly to all CPU cores:

- **cpu_history_measurement_interval** (default 5 minutes) - Interval at which average CPU utilization is computed and stored
- **cpu_history_duration** (default 60 minutes) - Total duration of historical data maintained
- **max_history_entries** (12 entries) - Calculated as cpu_history_duration / cpu_history_measurement_interval (60/5 = 12)

**Per-Core History Maintenance**

- **Granularity:** Each logical CPU core (cpu0, cpu1, ..., cpuN) maintains its own independent circular buffer
- **Storage Location:** STATE_DB (in-memory, non-persistent)
- **Data Structure:** Circular buffer with fixed size determined by system configuration

**Computation Logic**

**Step 1: Periodic Sampling**

Every 5 seconds, the daemon:
- Reads `/proc/stat` and computes instantaneous CPU utilization for each logical core
- Appends the computed utilization sample to a per-core history list

**Step 2: Average Calculation**

For each core, compute the average utilization over the measurement interval:

utilization = 100.0 * (total_delta - idle_delta) / total_delta


Where:
- `idle_delta` = Difference in idle time (in jiffies) between two consecutive reads
- `total_delta` = Difference in total CPU time (in jiffies) between two consecutive reads

**Step 3: Storage in Circular Buffer**

The computed average is stored in the next available slot in the core's circular buffer. Each buffer entry contains:
- **Timestamp:** When the measurement interval ended
- **Average CPU Utilization (%):** For that core during the interval

**Circular Buffer Behavior**

Buffer Structure (per core):

Buffer Index : [0] [1] [2] [3] ... [10] [11] 
Time Slots   : T=0 T=5 T=10 T=15 ... T=50 T=55

Buffer Size: cpu_history_duration / cpu_history_measurement_interval = 60 / 5 = 12 entries

**Eviction Policy:**

When the buffer is full (12 entries), the oldest entry is explicitly deleted from STATE_DB and removed from the buffer before the new entry is inserted

Example: At T=60, entry at index [0] (T=0) is explicitly deleted and replaced with new data

**Timeline Example** (defaults: duration=60 min, interval=5 min):

T=0 T=5 T=10 T=15 ... T=55 T=60 (deletes T=0, inserts new)
[s0] [s1] [s2] [s3] ... [s11] [s0'] ← oldest deleted, new inserted

#### 5.2.2 Memory Utilization Monitoring

**Current Snapshot (FR-3):**

The daemon monitors system-level physical memory (RAM) by periodically reading and parsing `/proc/meminfo`. 
It computes memory availability, usage, and utilization percentage to provide real-time memory statistics.

**Data Source:** `/proc/meminfo`

**Relevant Fields:**

- **MemTotal** - Total physical RAM installed on the system (in kB)
- **MemAvailable** - Estimate of memory available for starting new applications without swapping (in kB)

*Note: MemAvailable is preferred over MemFree as it accounts for reclaimable memory (buffers, caches) and provides a more accurate representation of usable memory.*

**Computation Logic**

**Metrics Calculated:**

- **Total Physical RAM:**
total_ram = MemTotal (from /proc/meminfo)


- **Available Memory:**
available_memory = MemAvailable (from /proc/meminfo)


- **Used Memory:**
used_memory = MemTotal − MemAvailable


- **Memory Utilization Percentage:**
usage_percent = (used_memory / total_ram) × 100


**Polling Mechanism**

- **Polling Interval:** 5 seconds (System-wide)
- **Precision:** Kilobytes (kB) - As provided by `/proc/meminfo`

**Rationale for 5-Second Interval**

- **System Overhead:** Minimal CPU impact; `/proc/meminfo` read is a lightweight operation

**Store in STATE_DB:** Update memory snapshot in STATE_DB

**Example Workflow**

- **T=0** - Daemon starts; initial read of `/proc/meminfo`
- Parses: MemTotal=16384000 kB, MemAvailable=8192000 kB
- Computes: used=8192000 kB, usage%=50%
- Stores snapshot in STATE_DB

- **T=5** - Second poll triggered
- Reads updated values from `/proc/meminfo`
- Recalculates metrics
- Updates STATE_DB snapshot

- **T=10** - Third poll...
- (continues every 5 seconds)

**Key Considerations**

- **System-Level Only:** Single memory snapshot for entire system (not per-process or per-core)
- **Current Snapshot Only:** No historical data maintained for FR-3
- **MemAvailable vs MemFree:** Uses MemAvailable for more accurate available memory estimation
- **Unit Consistency:** All values stored in kB (raw). Converted to MB/GB by the Management Interfaces for flexibility
- **Non-Persistent:** Snapshot resets on daemon restart
- **Lightweight Operation:** Minimal performance impact with 5-second polling

**History (FR-4):**

Same circular-buffer mechanism as CPU history, storing average memory utilization percentage per interval.

#### 5.2.3 Storage/Disk Utilization Monitoring

**Current Snapshot (FR-5):**

Retrieve storage partition information and utilization for all permanently attached storage devices. Report number of partitions per device and utilization percentage of each mounted partition. Removable devices excluded.

**Detailed Design Specification**

**1. Design Approach and Data Collection Strategy**

The daemon shall perform filesystem statistics collection on mounted partitions using system-level APIs equivalent to `os.statvfs()` functionality. The implementation follows a multi-stage discovery and filtering pipeline to identify qualifying storage devices, enumerate their partitions, and calculate utilization percentages while excluding removable media and pseudo-filesystems.

- **Scope:** Permanently attached block storage devices only
- **Exclusions:** Removable devices, pseudo/virtual filesystems, RAM-based filesystems

**2. Discovery and Filtering Pipeline**

**2.1 Stage 1: Mount Point Discovery**

- **Input Source:** `/proc/mounts` filesystem table
- **Parse Format:** Space-separated fields per line
    - **Field 1:** Device path (e.g., `/dev/sda1`)
    - **Field 2:** Mount point (e.g., `/`, `/home`)
    - **Field 3:** Filesystem type (e.g., `ext4`, `xfs`, `btrfs`)
     - **Remaining fields:** Mount options and metadata
- **Action:** Read entire file and parse each line to extract device, mount point, and filesystem type

**2.2 Stage 2: Device Type Filtering (Inclusion Criteria)**

Accept only block devices matching these path patterns:

- `/dev/sd*` - SCSI/SATA disks (e.g., `/dev/sda1`, `/dev/sdb2`)
- `/dev/hd*` - IDE/PATA disks (legacy support)
- `/dev/nvme*` - NVMe solid-state drives (e.g., `/dev/nvme0n1p1`)
- `/dev/mmcblk*` - eMMC/SD block devices (e.g., `/dev/mmcblk0p1`)
- `/dev/vd*` - VirtIO virtual disks (e.g., `/dev/vda1`)
- `/dev/xvd*` - Xen virtual disks (e.g., `/dev/xvda1`)

**Rationale:**
- `hd*`: Supports legacy IDE/PATA systems
- `vd*`, `xvd*`: Supports virtualized environments (KVM, Xen)

**Action:** Filter parsed mount entries to include only devices matching above patterns

**2.3 Stage 3: Filesystem Type Exclusion**

Exclude the following pseudo/virtual filesystems:

**By Filesystem Type:**
- `tmpfs` - Temporary RAM-based filesystem
- `devtmpfs` - Device filesystem in RAM
- `squashfs` - Compressed read-only filesystem (used for SONiC image)
- `overlay` - Union/overlay filesystem (used for Docker containers)
- `iso9660` - ISO 9660 CD-ROM filesystem

**By Mount Point Prefix:**
- `/dev` - Device filesystem
- `/proc` - Process information pseudo-filesystem
- `/sys` - Kernel system information pseudo-filesystem (includes `sysfs`)
- `/run` - Runtime data directory (includes `devpts`, `cgroup`, `cgroup2`)

**Rationale:**
- Mount point filtering catches filesystems even if type detection varies
- Excludes SONiC's SquashFS-based root image
- Prevents monitoring of container overlay filesystems

**Action:** Remove entries where filesystem type matches any excluded type

**2.4 Stage 4: Removable Device Detection**

- **Input Source:** `/sys/block/<device_name>/removable`

**Device Name Extraction Logic:**

Strip partition number from device path

- Example: `/dev/sda1` → `sda`
- Example: `/dev/nvme0n1p1` → `nvme0n1`
- Example: `/dev/mmcblk0p2` → `mmcblk0`

**Removable Flag Check:**

Read sysfs attribute value:
- `1` = Removable device (USB drives, external disks) → **EXCLUDE**
- `0` = Permanently attached device → **INCLUDE**

**Action:** For each qualifying device, read corresponding sysfs removable attribute and exclude if value is 1

**2.5 Stage 5: Mount Point Priority Selection**

Select the highest-priority mount point when multiple mounts exist for the same device path.

**Mount Point Priority:**

| Priority | Mount Point    | Rationale                   |
|-  -------|----------------|-----------------------------|
|10        |/               |Root filesystem              |
|9         |/host           |SONiC host filesystem access |
|8         |/boot           |Boot partition               |
|7         |/var/lib/docker |Docker storage               |
|6         |/home           |User data                    |
|5         |/usr            |System programs              |
|4         |/var            |Variable data                |
|3         |/tmp            |Temporary files              |
|2         |/opt            |Optional software            |
|1         |All others      |Default priority             |

**Action:**  For each qualifying device, calculate mount priority and retain only highest-priority mount for STATE_DB storage. Discard lower-priority duplicates.

**3. Utilization Calculation Methodology**

**3.1 Data Acquisition per Mount Point**

For each qualifying mount point that passed all filtering stages, retrieve filesystem statistics using `statvfs()` equivalent API.

**Required Metrics from statvfs structure:**

- `f_blocks` - Total data blocks in filesystem
- `f_bfree` - Free blocks available (including reserved)
- `f_bavail` - Free blocks available to non-privileged users
- `f_frsize` - Fundamental filesystem block size (in bytes)

**3.2 Calculation Formula**
Used Blocks = f_blocks - f_bfree Utilization Percentage = (Used Blocks / f_blocks) × 100


**Precision:** Round to 2 decimal places for reporting

**3.3 Edge Case Handling**

- **Division by zero:** If `f_blocks == 0`, report utilization as 0% or mark as N/A
- **Reserved space consideration:** Use `f_bavail` instead of `f_bfree` if reporting effective user-available utilization
- **Full filesystem:** Cap maximum at 100% (some filesystems may report over-commitment)
- **Negative values:** Python's os.statvfs() returns unsigned integers; negative values are not expected. If corrupted filesystem metadata causes negative calculations, the value is logged via exception handler and partition is skipped for current cycle

**4. Data Aggregation and Grouping Logic**

**4.1 Partition-to-Device Mapping**

**Base Device Extraction Rules:**

The system extracts base device names (without `/dev/` prefix) from partition paths:

- **Pattern:** `sd[a-z][0-9]*` → Base device name (e.g., `/dev/sda1` → `sda`)
- **Pattern:** `nvme[0-9]+n[0-9]+p[0-9]*` → Base device name (e.g., `/dev/nvme0n1p1` → `nvme0n1`)
- **Pattern:** `mmcblk[0-9]+p[0-9]*` → Base device name (e.g., `/dev/mmcblk0p2` → `mmcblk0`)

**Extraction Method:**
- Remove `/dev/` prefix from partition path
- Apply regex pattern matching to identify base device name
- Store base device name without `/dev/` prefix for internal tracking

**Grouping Strategy:**

Group all qualifying partitions by their parent base device. Maintain list of partition details under each base device.

**Example Output Structure:**

Base Device: sda
├─ Partition: /dev/sda1 (Mount: /, Utilization: 45.67%)
├─ Partition: /dev/sda2 (Mount: /home, Utilization: 78.23%)
└─ Partition Count: 2

Base Device: nvme0n1
├─ Partition: /dev/nvme0n1p1 (Mount: /boot/efi, Utilization: 12.34%)
└─ Partition Count: 1

**4.2 Partition Count Calculation**

- **Per-Device Count:** Total number of qualifying mounted partitions belonging to each base device.
- **Count Determination:Partition count is implicitly determined by counting STATE_DB entries per base device.
    # Count partitions for device 'sda'
    redis-cli -n 6 KEYS "STORAGE_TABLE|sda|*" | wc -l
- **Count Criteria:** Include only partitions that successfully passed all four filtering stages
- **Unmounted Partitions:** Do not include in count (only mounted partitions are considered)

**5. Input Data Sources and Access Methods**

- **`/proc/mounts`** - List all mounted filesystems
  - Read file, parse lines
  - Device path, mount point, FS type
  - Each polling cycle
  - Error handling: If read fails, log error and skip partition discovery for current cycle

- **`/sys/block/<dev>/removable`** - Determine if device is removable
  - Read sysfs file
  - Binary flag (0/1)
  - Per device, each cycle
  - Error handling: If file doesn't exist or read fails, assume device is permanent

- **`statvfs()` system call** - Filesystem utilization statistics
  - System call per mount point
  - Block counts (`f_blocks`, `f_bfree`, `f_bavail`, `f_frsize`)
  - Per mount point, each cycle
  - Error handling: OSError or ValueError causes partition skip for current cycle, retry next cycle

**Access Permissions Required:**

- Read access to `/proc/mounts` (typically world-readable; if denied, partition discovery fails)
- Read access to `/sys/block/*/removable` (typically world-readable; if denied, device treated as permanent)
- Execute permission for `statvfs()` on mount points (typically available to all users; if denied, partition skipped and retried next cycle))

**6. Output Data Structure and Format**

**6.1 Per-Partition Information**

Each partition entry shall contain:

- **Device name** (string): Base device name without /dev/ prefix, e.g., sda
- **Partition name** (string): Full device path, e.g., /dev/sda1
- **Mount point** (string): Absolute path, e.g., /home
- **Filesystem type** (string): e.g., ext4, xfs, btrfs
- **Total memory** (string, uint64): Total partition size in bytes, e.g., 107374182400
- **Used memory** (string, uint64): Used space in bytes, e.g., 48985497600
- **Available memory** (string, uint64): Available space in bytes, e.g., 58388684800
- **Utilization percentage** (string, float): 2 decimals, e.g., 45.67
- **Alarm status** (string, enum): active or cleared
- **Timestamp** (string, ISO 8601): Last update time in UTC, e.g., 2024-12-25T10:30:15Z

Memory Calculations:

Total memory = f_blocks × f_frsize
Used memory = (f_blocks - f_bfree) × f_frsize
Available memory = f_bavail × f_frsize

**6.2 Per-Device Summary**

Device-level information is derived implicitly:

- **Base device name** (string): e.g., sda (without /dev/ prefix)
- **Partition count** (integer): Derived by counting STATE_DB entries with matching base device
- **Partitions list** : Implicit collection of separate STATE_DB entries per partition

**6.3 Report Format**

Output is organized with flat key structure, enabling hierarchical queries:

**STATE_DB Key Format:**

- STORAGE_TABLE|<base_device_name>|<partition_path>

**Device-level aggregation (derived via queries):**

- **Base device name**: Extracted from key prefix (e.g., sda)
- **Partition count**: Count of matching keys for device
- **Query**: redis-cli -n 6 KEYS "STORAGE_TABLE|sda|*" | wc -l

**Partition-level details (per STATE_DB entry):**

- Individual partition information stored as hash fields
- Device path, mount point, filesystem type
- Memory metrics (total, used, available in bytes)
- Utilization percentage and alarm status

**7. Error Handling and Exception Scenarios**

**7.1 Runtime Error Conditions**

- **Mount point no longer exists** - `statvfs()` returns error → Skip partition, continue processing → Warning
- **Permission denied (sysfs)** - File read error on /sys/block/*/removable → Assume device is permanent, continue processing → Warning
- **Malformed `/proc/mounts` line** - Parse exception on line split → Skip line silently, continue to next → No log
- **File read error /proc/mounts** -  Exception during file open/read → Skip partition discovery for current cycle → Error
- **Race condition (unmount during scan)** - Mount point access error → Skip partition, retry next cycle → Warning
- **Corrupted statvfs data** -  Invalid block counts (negative/zero) → Skip partition for current cycle → Error
- **Device name extraction failure** - Regex/pattern match fails → Use fallback (original path), continue processing → No log

**7.2 Validation Checks**

- Verify `/proc/mounts` is readable via exception handling during parse
- Validate all parsed device paths match expected patterns (/dev/*)
- Confirm statvfs values are non-negative (no negative block counts)
- Check for duplicate devices and select mount point by priority

**8. Performance Optimization Considerations**

**8.1 Execution Strategy**

- **Polling Interval:** 5 seconds (configurable via DEFAULT_SRM_POLLING_INTERVAL_SECS)
- **Execution Model:** Sequential processing - statvfs() calls executed serially per partition
- **Resource Impact:** Minimal - lightweight read operations on sysfs, proc filesystems, and statvfs() system calls

**8.2 Caching and Efficiency**

- **Device Discovery Cache:** Device-to-partition mappings discovered once during daemon initialization and reused across cycles
- **Per-Cycle Execution:** Each monitoring cycle uses cached device mappings, only calls statvfs() for runtime data
- **File Reading:**  Standard Python file I/O with default buffering for /proc/mounts and sysfs reads

**8.3 Concurrency Considerations**

- **Single-threaded:** All operations execute sequentially in main daemon loop
- **Non-blocking:** Daemon uses event-based waiting (stop_event.wait()) between cycles
- **Lock-free reads:** No locking required - all data sources are read-only

**9. Testing and Validation Requirements**

**9.1 Test Scenario Inputs**

**System Configuration Scenarios:**

- Systems with mixed storage types: SATA + NVMe + removable USB simultaneously
- Multiple partitions per device: 3+ partitions on single `/dev/sda`
- High utilization scenarios: Filesystems at >95% capacity
- Uncommon filesystem types: btrfs, zfs, xfs, f2fs
- Complex mount scenarios: Bind mounts (same partition mounted multiple times)
- Dynamic scenarios: Hot-plug/unplug events during monitoring cycle
- Edge systems: eMMC-only devices (embedded systems, Raspberry Pi)

**9.2 Validation Checkpoints**

- Verify correct exclusion of all removable devices
- Confirm accurate partition counts per device
- Validate utilization percentages against `df -h` output
- Test with empty/zero-block filesystems
- Verify behavior with read-only mounted partitions

**9.3 Expected Behavior Verification**

- All permanently attached devices discovered
- All pseudo-filesystems excluded
- Partition counts match actual device partition tables
- Utilization percentages accurate to ±0.01% (2 decimal precision)
- No false positives from removable devices

**10. Implementation Checklist**

Developer shall implement the following in sequence:

- ✓ Parse `/proc/mounts` and extract device, mount point, filesystem type
- ✓ Apply device path pattern filtering (`/dev/sd*`, `/dev/nvme*`, `/dev/mmcblk*`)
- ✓ Apply filesystem type exclusion list
- ✓ Extract base device name from partition device paths
- ✓ Read and check `/sys/block/<device>/removable` flag
- ✓ Execute `statvfs()` on each qualifying mount point
- ✓ Calculate utilization percentage using formula
- ✓ Group partitions by base device
- ✓ Count partitions per device (implicit via STATE_DB key queries)
- ✓ Format output according to specified data structure
- ✓ Implement error handling for all identified scenarios
- ✓ Add logging at appropriate levels
- ✓ Validate against test scenarios


#### 5.2.4 Threshold-Based Alarming

Three independent thresholds are supported:

- **CPU** - CONFIG_DB Key: `CPU_GLOBAL|global` - Field: `cpu_utilization_threshold`- Default: 85% 
- **Memory** - CONFIG_DB Key: `SYSTEM_RESOURCE_THRESHOLD|MEMORY` - Default: 80% - Alarm ID: `MEMORY_UTILIZATION_HIGH`
- **Disk** - CONFIG_DB Key: `STORAGE_GLOBAL|global, Field: `storage_utilization_threshold` - Default: 75% - Alarm Status: active or cleared

**Alarm lifecycle:**
      current >= threshold
CLEARED ─────────────────────────► ACTIVE
  ▲                                   │
  │        current < threshold        │
  └───────────────────────────────────┘

**Alarm Transitions:**

- **On transition CLEARED → ACTIVE:** Update `alarm_status` field to `active` in `CPU_TABLE` in STATE_DB, emit syslog `LOG_ALERT`
- **On transition ACTIVE → CLEARED:** Update `alarm_status` field to `cleared` in `CPU_TABLE` in STATE_DB, emit syslog `LOG_INFO`
- **Alarm flapping protection:** No alarm flapping protection is implemented in v1.0; debounce may be added in future revisions
- **On transition CLEARED → ACTIVE:** Update alarm_status field in STORAGE_TABLE to "active", emit syslog LOG_WARNING
- **On transition ACTIVE → CLEARED:** Update alarm_status field in STORAGE_TABLE to "cleared", emit syslog LOG_NOTICE
- **Alarm flapping protection:** No alarm flapping protection is implemented; alarm state can transition every monitoring cycle (5 seconds)

**Disk Threshold Application:**

For **disk**, The threshold applies to each mounted partition independently. If any single partition exceeds the threshold, its alarm_status field is set to "active" identifying that specific partition.

** Disk Alarm Identification:**

- **Resource ID Format:**<base_device>|<partition_path> (e.g., sda|/dev/sda1)
- **STATE_DB Storage:** Alarm status stored in STORAGE_TABLE|<base_device>|<partition_path> entry



#### 5.2.8 Syslog Notifications

All threshold events produce syslog entries via the Python `syslog` module:

**Alarm raised (Three syslog entries emitted):**
<WARNING> pmon#platformd: ALARM RAISED: CPU_UTILIZATION | Resource: 0|0 | Current: 90% | Threshold: 85% | CPU utilization exceeded threshold

<ALERT> pmon#platformd: ALARM RAISED: CPU_UTILIZATION | Resource: 0|0 | Current: 90% | Threshold: 85% | CPU utilization exceeded threshold

<WARNING> pmon#platformd: PLATFORM_ALARM: type=CPU_UTILIZATION, resource=0|0, action=raised, current=90, threshold=85

**Alarm cleared (Three syslog entries emitted):**
<WARNING> pmon#platformd: ALARM CLEARED: CPU_UTILIZATION | Resource: 0|0 | Current: 31% | Threshold: 85% | CPU utilization returned to normal

<INFO> pmon#platformd: ALARM CLEARED: CPU_UTILIZATION | Resource: 0|0 | Current: 31% | Threshold: 85% | CPU utilization returned to normal

<INFO> pmon#platformd: PLATFORM_ALARM: type=CPU_UTILIZATION, resource=0|0, action=cleared, current=31, threshold=85


**Disk example (per-partition):**
**Alarm raised:**
<WARNING> pmon#stormond[40]: STORAGE ALARM ACTIVE: sda|/dev/sda3 utilization 79.65% exceeds threshold 75.0%
<INFO> pmon#stormond[40]: SRM Storage: sda|/dev/sda3 - Utilization: 80.73%, Alarm: active

**Alarm cleared:**
<NOTICE> pmon#stormond[40]: STORAGE ALARM CLEARED: sda|/dev/sda3 utilization 69.36% is below threshold 75.0%
<INFO> pmon#stormond[40]: SRM Storage: sda|/dev/sda3 - Utilization: 68.36%, Alarm: cleared

**Syslog Configuration:**

Syslog facility: LOG_DAEMON (standard for system daemons)(`LOG_WARNING` for raise, `LOG_NOTICE` for clear).
Severity Mapping: Alarm raised: LOG_WARNING , Alarm cleared: LOG_INFO (mapped to NOTICE level via daemon logger)
Identifier: stormond (storage monitoring daemon)
Format: <resource_type> ALARM <state>: <resource_id> utilization <value>% <comparison> threshold <threshold>%
Resource ID Format:Storage alarms use the format <base_device>|<partition_path>

---
#### 5.3 Target Deployment Use Cases
1. **Network Operations Center (NOC) Monitoring** — Operators query real-time and historical CPU/memory metrics to diagnose control-plane performance issues.
2. **Capacity Planning** — Historical utilization data helps architects right-size platforms.
3. **Proactive Alerting** — Threshold alarms trigger syslog messages consumed by external NMS/SIEM systems for early anomaly detection.
4. **Hardware Health Dashboards** — CPU, RAM, and Storage metrics feed into dashboards for platform resource monitoring

---
#### 5.4 Scalability Requirements

- The feature shall support systems with up to **256 logical CPU cores**.
- The feature shall support systems with up to 50 storage partitions across multiple devices
- History circular buffer: max entries = `cpu_history_duration  / cpu_history_measurement_interval` per core (default 12 entries per core for CPU; 12 entries for memory)

#### 5.4.1 Redis Memory Footprint Estimation

Assumptions for a system with **128 logical CPU cores**, default history settings (duration=60 min, interval=5 min → 12 entries), and 10 storage partitions.

| STATE_DB Table                      | Keys                                 | Estimated Size per Key | Total       |
|-------------------------------------|--------------------------------------|------------------------|-------------|
| `CPU_GLOBAL`                        | 1                                    | ~150 bytes             | ~0.15 KB    |
| `CPU_TABLE`                         | 128                                  | ~150 bytes             | ~19 KB      |
| `CPU_HISTORY_TABLE`                 | 128 × 12 = 1,5336                    | ~200 bytes             | ~300 KB     |
| `RAM_GLOBAL`                        | 1                                    | ~200 bytes             | ~0.2 KB     |
| `STORAGE_TABLE`                     | 10                                   | ~400 bytes             | ~4KB        |
| `STORAGE_INFO`                      | 3                                    | ~300 bytes             | ~0.9 KB     |
| `SYSTEM_RESOURCE_ALARM`             | ~13 (CPU + MEM + 10 DISK + 1 buffer) | ~300 bytes             | ~4 KB       |
| **Total**                           |                                      |                        | **~329 KB** |

With maximum configurable history (duration=1440 min, interval=1 min → 1440 entries):

| Table                               | Keys                 | Total      |
|-------------------------------------|----------------------|------------|
| `CPU_HISTORY_TABLE`                 | 128 × 1440 = 184,320 | ~36 MB     |
| `RAM_HISTORY_TABLE`                 | 1,440                | ~350 KB    |
| **Total (max config)**              |                      | **~37 MB** |

This is within acceptable Redis memory bounds. A validation warning should be emitted if the operator configures very large history windows on systems with many cores.

##### 5.4.2 CPU Overhead

| Operation                               | Frequency        | Estimated CPU Time |
|-----------------------------------------|------------------|------------ -------|
| Read `/proc/stat` (128 cores)           | Every 5 seconds  | < 1 ms             |
| Read `/proc/meminfo`                    | Every 5 seconds  | < 0.5 ms           |
| `os.statvfs()` × 10 partitions          | Every 5 seconds  | < 2 ms             |
| History write (128 cores × 1 entries)   | Every 5 minutes  | < 50 ms            |
| Threshold evaluation                    | Every 5 seconds  | < 1 ms             |
| **Total per cycle**                     |                  | **< 5 ms**         |

The daemon consumes negligible CPU resources (< 0.1 % of a single core).

---

### 6. Architecture Design

**Architecture diagram flow:**

┌─────────────────────────────────────────────────────────┐
│                    Management Layer                     │
│              (CLI, gNMI, SNMP, REST API)                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                        CONFIG_DB                        │
│              (Thresholds, History Config)               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              PMON Container                             │
│  ┌──────────────────────────────────────────────┐       │
│  │            platformd                         │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │  Metric Collectors:                    │  │       │
│  │  │  - CPU Monitor (/proc/stat)            │  │       │
│  │  │  - Memory Monitor (/proc/meminfo)      │  │       │
│  │  │  - Disk Monitor (os.statvfs())         │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │  History Manager                       │  │       │
│  │  │  - Circular buffer storage             │  │       │
│  │  │  - Configurable intervals              │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  │  ┌────────────────────────────────────────┐  │       │
│  │  │  Threshold Alarm Manager               │  │       │
│  │  │  - CPU threshold monitoring            │  │       │
│  │  │  - Memory threshold monitoring         │  │       │
│  │  │  - Disk threshold monitoring           │  │       │
│  │  │  - Syslog notification                 │  │       │
│  │  └────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────┘       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                     STATE_DB                            │
│  (Current Metrics, History Data, Alarm Status)          │
└─────────────────────────────────────────────────────────┘


#### 6.1 Basic Approach

A new Python daemon — **`platformd`** — is introduced. It runs inside the **PMON container** and periodically collects CPU, memory, and disk metrics from the Linux kernel. It stores current snapshots and historical averages in **STATE_DB**, monitors configurable thresholds, and raises/clears alarms via **syslog** and Alarm status is stored as a field within the respective resource tables in STATE_DB.

#### 6.2 Container

| Component                  | Location                                            |
|----------------------------|-----------------------------------------------------|
| `platformd`                | `pmon` container                                    |
| CLI                        | `sonic-cli` / Click framework                       |
| YANG / REST / gNMI         | `sonic-mgmt-framework` container                    |

### 7 High-Level Design

#### 7.1 Overview

┌───────────────────────────────────────────────────────────────────────────┐
│                              SONiC System                                 │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        pmon container                               │  │
│  │                                                                     │  │
│  │  ┌────────────────────────────────────────────────────────────┐     │  │
│  │  │                platformd  (Python daemon)                  │     │  │
│  │  │                                                            │     │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │     │  │
│  │  │  │CPU Collector│  │RAM Collector│  │  Storage Collector  │ │     │  │
│  │  │  │ /proc/stat  │  │/proc/meminfo│  │ os.statvfs()        │ │     │  │
│  │  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │     │  │
│  │  │         │                │                    │            │     │  │
│  │  │         └────────────────┼────────────────────┘            │     │  │
│  │  │                          ▼                                 │     │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │     │  │
│  │  │  │                  History Engine                      │  │     │  │
│  │  │  │    Circular buffer: per interval, per resource       │  │     │  │
│  │  │  └─────────────────────────┬────────────────────────────┘  │     │  │
│  │  │                            ▼                               │     │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │     │  │
│  │  │  │           Threshold / Alarm Engine                   │  │     │  │
│  │  │  │   Compare current vs CONFIG_DB thresholds            │  │     │  │
│  │  │  │   Raise / clear alarms → syslog + STATE_DB           │  │     │  │
│  │  │  └─────────────────────────┬────────────────────────────┘  │     │  │
│  │  └────────────────────────────┼────────────────────────────── ┘     │  │
│  └───────────────────────────────┼─────────────────────────────────────┘  │
│                                  │                                        │
│                                  ▼                                        │
│            ┌──────────────────────────────────────────┐                   │
│            │           Redis (STATE_DB)               │                   │
│            │   • CPU_TABLE                            │                   │
│            │   • CPU_HISTORY_TABLE                    │                   │
│            │   • RAM_GLOBAL                           │                   │
│            │   • RAM_HISTORY_TABLE                    │                   │
│            │   • STORAGE_TABLE                        │                   │
│            └──────────────────────────────────────────┘                   │
│                                                                           │
│            ┌────────────────────────────────────────────┐                 │
│            │          Redis (CONFIG_DB)                 │                 │
│            │   • CPU_GLOBAL                             │                 │
│            │   • RAM_GLOBAL                             │                 │
│            │   • STORAGE_GLOBAL                         │                 │
│            └────────────────────────────────────────────┘                 │
│                                ▲                                          │
│                                │                                          │
│  ┌───────────────────────────────┴─────────────────────────────────────┐  │
│  │              sonic-mgmt-framework container                         │  │
│  │         REST API  /  gNMI  /  YANG transformer                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                          │
│                                │                                          │
│  ┌───────────────────────────────┴─────────────────────────────────────┐  │
│  │                    Click CLI (sonic-cli)                            │  │
│  │                                                                     │  │
│  │  show platform cpu | cpu-history | ram | ram-history | storage      │  │
│  │  config platform cpu | cpu-history | ram | ram-history | storage    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘

```

#### 7.2 DB Schema

##### 7.2.1 CONFIG_DB

**Table: CPU_GLOBAL**

Stores global monitoring configuration.

```
; Key
CPU_GLOBAL|global

; Fields
cpu_utilization_threshold        = 1*3DIGIT   ; percentage (1-100), default "85"
cpu_history_status               = "enabled" / "disabled" ; default "enabled"
cpu_history_measurement_interval = 1*3DIGIT   ; minutes, default "5"
cpu_history_duration     = 1*4DIGIT    ; minutes, default "60"
```

Example:
```json
{
  "CPU_GLOBAL|global": {
    ""cpu_utilization_threshold"":      "85",
    "cpu_history_status":               "enabled",
    "cpu_history_measurement_interval": "5",
    "cpu_history_duration":             "60"
  }
}
```
**Table:"STORAGE_GLOBAL" **

Stores storage monitoring threshold configuration.

; Key
"STORAGE_GLOBAL|global"
; Fields
"storage_utilization_threshold" = 1*3DIGIT    ; percentage (0-100), default "75"

Example:
```json
{
  "STORAGE_GLOBAL|global": {
    "storage_utilization_threshold": "75"
  }
}
```


##### 7.2.2 STATE_DB

**Table: CPU_TABLE**

Current snapshot per logical CPU core.

```
; Key format
CPU_TABLE|{cpu_index}|{core_index}
; e.g. "0|0", "0|1", "0|2"

; Fields
cpu_index       = 1*DIGIT              ; e.g. "0"
cpu_core_index  = 1*DIGIT              ; e.g. "0", "1", "2"
cpu_utilization = 1*3DIGIT             ; integer percentage e.g. "45"
alarm_status    = "active" / "cleared" ; current alarm state
timestamp       = ISO-8601             ; e.g. "2025-07-11T10:30:00Z"

```

**Table: CPU_HISTORY_TABLE**

Historical average CPU utilization per core.

```
; Key format
CPU_HISTORY_TABLE|{cpu_index}|{core_index}|{timestamp}
; e.g. "0|0|2026-06-04T13:01:10Z"

; Fields
cpu_index               = 1*DIGIT   ; e.g. "0"
cpu_core_index          = 1*DIGIT   ; e.g. "0", "1"
cpu_history_utilization = 1*3DIGIT  ; integer percentage e.g. "45"
timestamp               = ISO-8601  ; e.g. "2026-06-04T13:01:10Z"

```

**Table: SYSTEM_MEMORY_UTILIZATION**

Current snapshot of system memory.

```
; Key format
SYSTEM_MEMORY_UTILIZATION|system

; Fields
total_mb        = 1*10DIGIT
used_mb         = 1*10DIGIT
available_mb    = 1*10DIGIT
usage_percent   = 1*5CHAR
timestamp       = ISO-8601
```

**Table: SYSTEM_MEMORY_UTILIZATION_HISTORY**

Historical average memory utilization.

```
; Key format
SYSTEM_MEMORY_UTILIZATION_HISTORY|<index>

; Fields
avg_usage_percent = 1*5CHAR
avg_used_mb       = 1*10DIGIT
avg_available_mb  = 1*10DIGIT
interval_start    = ISO-8601
interval_end      = ISO-8601
```

**Table: STORAGE_TABLE**

Per-partition storage utilization for mounted partitions on permanent storage devices.

```
; Key format
STORAGE_TABLE|<base_device_name>|<partition_path>
; base_device_name = "sda", "nvme0n1", "mmcblk0", etc. (without /dev/ prefix)
; partition_path = full partition device path, e.g., "/dev/sda1"


; Fields
device_name         = base device name (string), e.g., "sda"
partition_name      = full partition path (string), e.g., "/dev/sda1"
mount_point         = absolute mount path (string), e.g., "/"
fstype              = filesystem type (string), e.g., "ext4"
total_memory        = total size in bytes (string uint64), e.g., "107374182400"
used_memory         = used space in bytes (string uint64), e.g., "48985497600"
available_memory    = available space in bytes (string uint64), e.g., "58388684800"
storage_utilization = utilization percentage (string float, 2 decimals), e.g., "45.67"
alarm_status        = "active" / "cleared"
timestamp           = ISO-8601 (string), e.g., "2024-12-25T10:30:15Z"
```

##### 7.2.3 COUNTERS_DB

No changes to COUNTERS_DB are required for this feature.

#### 7.3 Flow Diagrams

##### 7.3.1 Resource Collection Flow

```
                    ┌─────────────────────────┐
                    │       platformd         │
                    │       (startup)         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Load config from       │
                    │  CONFIG_DB              │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Clear stale STATE_DB   │
                    │  entries                │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │          Main Loop (every 5s)       │
              │                                     │
              │  ┌──────────┐ ┌─────────┐ ┌──────┐  │
              │  │ Read     │ │ Read    │ │Read  │  │
              │  │/proc/stat│ │/proc/   │ │os.   │  │
              │  │          │ │meminfo  │ │stat  │  │
              │  │          │ │         │ │vfs() │  │
              │  └────┬─────┘ └────┬────┘ └──┬───┘  │
              │       │            │         │      │
              │       ▼            ▼         ▼      │
              │  ┌──────────────────────────────┐   │
              │  │ Compute utilization %        │   │
              │  │ Write to STATE_DB (snapshot) │   │
              │  └──────────────┬───────────────┘   │
              │                 │                   │
              │     ┌───────────▼────────────┐      │
              │     │ Interval elapsed?      │      │
              │     │ (measure_interval)     │      │
              │     └───┬───────────┬────────┘      │
              │     YES │           │ NO            │
              │         ▼           │               │
              │  ┌──────────────┐   │               │
              │  │Write snapshot│   │               │
              │  │ to history   │   │               │
              │  │ STATE_DB     │   │               │
              │  └──────┬───────┘   │               │
              │         │           │               │
              │         ▼           ▼               │
              │  ┌──────────────────────────────┐   │
              │  │ Check thresholds vs config   │   │
              │  │ Raise/clear alarms           │   │
              │  │ Write alarm_status           │   │
              │  │ Emit syslog                  │   │
              │  └──────────────────────────────┘   │
              │                                     │
              │  ┌──────────────────────────────┐   │
              │  │  Read CONFIG_DB              │   │
              │  │ (thresholds, intervals, etc) │   │
              │  └──────────────────────────────┘   │
              │                                     │
              │     sleep(5 seconds)                │
              │     loop ↑                          │
              └─────────────────────────────────────┘
```

##### 7.3.2 Threshold Alarm Flow

```
    ┌──────────────────┐       ┌──────────────┐       ┌──────────────┐
    │  Daemon collects │       │  Compare     │       │  Alarm State │
    │  current metric  │─────▶ │  with        │─────▶│  Machine     │
    │  (CPU/Mem/Disk)  │       │  threshold   │       │              │
    └──────────────────┘       └──────────────┘       └──────┬───────┘
                                                             │
                               ┌─────────────────────────────┤
                               │                             │
                     ┌─────────▼─────────┐          ┌────────▼────────┐
                     │ current > thresh  │          │ current ≤ thresh│
                     │ AND prev=cleared  │          │ AND prev=active │
                     └─────────┬─────────┘          └────────┬────────┘
                               │                             │
                     ┌─────────▼─────────┐          ┌────────▼────────┐
                     │ Set alarm=active  │          │Set alarm=cleared│
                     │ Write STATE_DB    │          │ Write STATE_DB  │
                     │ syslog WARNING    │          │ syslog NOTICE   │
                     └───────────────────┘          └─────────────────┘
```


#### 7.4 Sequence Diagram

**Sequence 1: platformd Initialization**
```
┌──────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│ PMON │    │ platformd│    │ CONFIG_DB │    │ STATE_DB │
└──┬───┘    └────┬─────┘    └─────┬─────┘    └────┬─────┘
   │             │                │               │
   │ Start       │                │               │
   │ platformd   │                │               │
   ├────────────>│                │               │
   │             │                │               │
   │             │ Read CPU_GLOBAL│               │
   │             ├───────────────>│               │
   │             │                │               │
   │             │ Read RAM_GLOBAL│               │
   │             ├───────────────>│               │
   │             │                │               │
   │             │ Read           │               │
   │             │ STORAGE_GLOBAL │               │
   │             ├───────────────>│               │
   │             │                │               │
   │             │ Thresholds &   │               │
   │             │ History Config │               │
   │             │<───────────────┤               │
   │             │                │               │
   │             │ Clear stale STATE_DB entries   │
   │             ├───────────────────────────────>│
   │             │                │               │
   │             │ Start main     │               │
   │             │ loop (every 5s)│               │
   │             │─┐              │               │
   │             │ │              │               │
   │             │<┘              │               │
   │             │                │               │
   │   Ready     │                │               │
   │<────────────┤                │               │

```

**Sequence 2: Metric Collection and Threshold Monitoring**

```
┌──────────┐  ┌────────────┐  ┌────────┐  ┌────────┐
│platformd │  │   Linux    │  │STATE_DB│  │ Syslog │
│Collector │  │  Kernel    │  │        │  │        │
└────┬─────┘  └─────┬──────┘  └───┬────┘  └───┬────┘
     │              │             │           │
     │ Timer (5s)   │             │           │
     │──┐           │             │           │
     │  |           │             │           │
     │<─┘           │             │           │
     │              │             │           │
     │ /proc/stat   │             │           │
     ├─────────────>│             │           │
     │              │             │           │
     │ CPU data     │             │           │
     │<─────────────┤             │           │
     │              │             │           │
     │ /proc/meminfo│             │           │
     ├─────────────>│             │           │
     │              │             │           │
     │ RAM data     │             │           │
     │<─────────────┤             │           │
     │              │             │           │
     │ os.statvfs() │             │           │
     ├─────────────>│             │           │
     │              │             │           │
     │ Storage data │             │           │
     │<─────────────┤             │           │
     │              │             │           │
     │ Write CPU_TABLE            │           │
     ├───────────────────────────>│           │
     │              │             │           │
     │ Write RAM_GLOBAL           │           │
     ├───────────────────────────>│           │
     │              │             │           │
     │ Write STORAGE_TABLE        │           │
     ├───────────────────────────>│           │
     │              │             │           │
     │ Check thresholds           │           │
     │──┐           │             │           │
     │  |           │             │           │
     │<─┘           │             │           │
     │              │             │           │
     │ CPU > 85%    │             │           │
     │──┐           │             │           │
     │  │           │             │           │
     │<─┘           │             │           │
     │              │             │           │
     │ Write alarm_status to      │           │
     │ CPU_TABLE / RAM_GLOBAL /   │           │
     │ STORAGE_TABLE              │           │
     ├───────────────────────────>│           │
     │              │             │           │
     │ Emit syslog  │             │           │
     │ WARNING+ALERT│             │           │
     ├────────────────────────────────────────>
     │              │             │           │

```

**Sequence 3: History Data Collection**

```
┌─────────────┐  ┌────────────┐  ┌───────────┐
│  platformd  │  │  STATE_DB  │  │ CONFIG_DB │
│  (History   │  │            │  │           │
│   Engine)   │  │            │  │           │
└──────┬──────┘  └─────┬──────┘  └─────┬─────┘
       │               │               │
       │ Read history config           │
       ├──────────────────────────────>│
       │               │               │
       │ cpu_history_duration=60,      │
       │ cpu_history_measurement_      │
       │ interval=5                    │
       │ ram_history_duration=60,      │
       │ ram_history_measurement_      │
       │ interval=5                    │
       │<──────────────────────────────┤
       │              │                │
       │ Calculate max buffer size     │
       │ at startup                    │
       │ (60/5 = 12 entries)           │
       │──┐           │                │
       │  │           │                │
       │<─┘           │                │
       │              │                │
       │ Timer (cpu/ram_history_       │
       │ measurement_interval = 5 min) │
       │──┐           │                │
       │  │           │                │
       │<─┘           │                │
       │              │                │
       │ Append current CPU snapshot   │
       │ to history buffer             │
       │ Remove oldest if > 12 entries │
       │──┐           │                │
       │  │           │                │
       │<─┘           │                │
       │              │                │
       │ Write CPU_HISTORY_TABLE       │
       ├─────────────>│                │
       │              │                │
       │ Append current RAM snapshot   │
       │ to history buffer             │
       │ Remove oldest if > 12 entries │
       │──┐           │                │
       │  │           │                │
       │<─┘           │                │
       │              │                │
       │ Write RAM_HISTORY_TABLE       │
       ├─────────────>│                │
       │              │                │

```

### 8. SAI API 

No new SAI attributes or APIs are required. 

---

### 9. Configuration and Management
- All configurations shall be persisted in CONFIG_DB and survive warm/cold reboot.
- History data (CPU, RAM) shall be stored in STATE_DB and is **not** required to survive restart.
- CLI (Click), REST API, and gNMI interfaces shall be provided.
- YANG models shall be provided for CONFIG_DB validation and REST/gNMI schema.
#### 9.1 Daemon Design

##### 9.1.1 platformd

**Location:** Inside `pmon` container
**Language:** Python 3
**Managed by:** supervisord (inside `pmon` container)
**Dependencies:** `redis-server.service`, `database.service`

```
```
[Unit]
Description=SONiC Platform Monitor Daemon
After=database.service
Requires=database.service

[Service]
Type=simple
ExecStart=/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

**Initialization sequence:**

```
1.  Connect to CONFIG_DB and STATE_DB.
2. Load CPU configuration from CPU_GLOBAL|global.
3. Load RAM configuration from RAM_GLOBAL|global.
4. Load Storage configuration from STORAGE_GLOBAL|global.
5. Clear any stale entries from STATE_DB history tables
   (CPU_HISTORY_TABLE, RAM_HISTORY_TABLE).
6.  Discover logical CPU cores from /proc/stat.
7. Discover mounted storage partitions via os.statvfs().
8. Enter main loop (every 5 seconds).

```
**Main loop (simplified pseudocode):**

```python

class PlatformDaemon(daemon_base.DaemonBase):
    def __init__(self):
        self.config_db = daemon_base.db_connect(CONFIG_DB)
        self.state_db  = daemon_base.db_connect(STATE_DB)

        self.cpu_monitor = CPUMonitor(
            config_db=self.config_db,
            state_db=self.state_db
        )
        self.cpu_monitor.initialize()

        self.ram_monitor = RAMMonitor(
            config_db=self.config_db,
            state_db=self.state_db
        )
        self.ram_monitor.initialize()

        self.stop_event = threading.Event()

    def run(self):
            # --- Current Snapshot ---
        cpu_snapshot_thread = threading.Thread(
            target=self.cpu_monitor.update_snapshot
        )

            # --- History ---
        cpu_history_thread = threading.Thread(
            target=self.cpu_monitor.update_history
        )

        # Start all threads
        cpu_snapshot_thread.start()
        cpu_history_thread.start()
        ram_snapshot_thread.start()
        ram_history_thread.start()

        # Main thread waits for stop signal (SIGTERM/SIGINT)
        while not self.stop_event.wait(1):
            pass
```

##### 9.1.2 Collection and History Engine

**CPU Collection:**

```python
class CPUMonitor:
    def update_snapshot(self):    # snapshot collection is inside CPUMonitor
        """
        Read /proc/stat, compute per-core utilization delta,
        update CPU_TABLE in STATE_DB.
        """
    with open('/proc/stat', 'r') as f:
            lines = f.readlines()

        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        cpu_table = swsscommon.Table(self.state_db, CPU_TABLE)

        for line in lines:
            if line.startswith('cpu') and not line.startswith('cpu '):
                parts = line.split()
                core_name = parts[0]          # e.g. 'cpu0'

                if core_name not in self.cpu_cores:
                    continue

                cpu_core = self.cpu_cores[core_name]

                # Parse CPU times from /proc/stat
                user    = int(parts[1])
                nice    = int(parts[2])
                system  = int(parts[3])
                idle    = int(parts[4])
                iowait  = int(parts[5])
                irq     = int(parts[6])
                softirq = int(parts[7])
                steal   = int(parts[8]) if len(parts) > 8 else 0

                total     = user + nice + system + idle + iowait + irq + softirq + steal
                idle_time = idle + iowait

                # For CPU delta calculation:
                #   total_delta = total - last_total
                #   idle_delta  = idle  - last_idle
                #   utilization = 100 * (total_delta - idle_delta) / total_delta
                #   clamped to [0, 100] as int
                if cpu_core.last_total != 0:
                    total_delta = total - cpu_core.last_total
                    idle_delta  = idle_time - cpu_core.last_idle

            if total_delta > 0:
                        utilization = 100.0 * (total_delta - idle_delta) / total_delta
                        cpu_core.current_utilization = min(100, max(0, int(round(utilization))))

                # Update last values for next delta
                cpu_core.last_total = total
                cpu_core.last_idle  = idle_time

                # Accumulate for history average
                if self.history_enabled:
                    cpu_core.history_accumulator.append(cpu_core.current_utilization)

                # Write CPU_TABLE to STATE_DB:
                #   key   = cpu_index|core_index
                #   fields= cpu_index, cpu_core_index,
                #           cpu_utilization, alarm_status, timestamp
                key          = cpu_core.get_key()  # f"{cpu_index}|{core_index}"
                alarm_status = self.alarm_states.get(key, 'cleared')

                fvs = swsscommon.FieldValuePairs([
                    ('cpu_index',       str(cpu_core.cpu_index)),
                    ('cpu_core_index',  str(cpu_core.core_index)),
                    ('cpu_utilization', str(cpu_core.current_utilization)),
                    ('alarm_status',    alarm_status),
                    ('timestamp',       timestamp)
                ])
                cpu_table.set(key, fvs)

**History Recording (Circular Buffer):**

```python
class CPUMonitor:
    def update_history(self):   # history recording is inside CPUMonitor
        if not self.history_enabled:
            return

        timestamp     = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        history_table = swsscommon.Table(self.state_db, CPU_HISTORY_TABLE)

        for core_name, cpu_core in self.cpu_cores.items():

            # Compute average from accumulator
            if cpu_core.history_accumulator:
                avg_utilization = int(round(
                    sum(cpu_core.history_accumulator) /
                    len(cpu_core.history_accumulator)
                ))
        else:
                avg_utilization = cpu_core.current_utilization

            # Circular buffer (deque):
            #   if full → remove oldest from buffer AND STATE_DB
            if len(cpu_core.history_buffer) >= self.max_history_entries:
                oldest_entry = cpu_core.history_buffer.popleft()
                old_key = f"{cpu_core.get_key()}|{oldest_entry['timestamp']}"
                history_table._del(old_key)

            # Append new entry to buffer
            cpu_core.history_buffer.append({
                'timestamp':   timestamp,
                'utilization': avg_utilization
            })

            # Write new entry to CPU_HISTORY_TABLE
            key = f"{cpu_core.get_key()}|{timestamp}"
            fvs = swsscommon.FieldValuePairs([
                ('cpu_index',               str(cpu_core.cpu_index)),
                ('cpu_core_index',          str(cpu_core.core_index)),
                ('timestamp',               timestamp),
                ('cpu_history_utilization', str(avg_utilization))
            ])
            history_table.set(key, fvs)

            # Clear accumulator for next interval
            cpu_core.history_accumulator.clear()
```

**Memory Collection:**

```python
def collect_memory_snapshot(self):
    meminfo = {}
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            parts = line.split()
            key = parts[0].rstrip(':')
            val = int(parts[1])  # kB
            meminfo[key] = val

    total_mb     = meminfo['MemTotal'] // 1024
    available_mb = meminfo['MemAvailable'] // 1024
    used_mb      = total_mb - available_mb
    usage_pct    = round(100.0 * used_mb / total_mb, 2) if total_mb > 0 else 0

    self.state_db.set(self.state_db.STATE_DB,
        "SYSTEM_MEMORY_UTILIZATION|system", {
            "total_mb": str(total_mb),
            "used_mb": str(used_mb),
            "available_mb": str(available_mb),
            "usage_percent": str(usage_pct),
            "timestamp": iso_now()
    })
    self.mem_accum.append(usage_pct)
```

**Storage Collection:**

```python
def collect_storage_snapshot(self):
    partitions = self.discover_permanent_partitions()
    devices = {}  # device -> set of partitions

    for part in partitions:
        vfs = os.statvfs(part.mount_point)
        total_blocks = vfs.f_blocks
        free_blocks  = vfs.f_bfree
        if total_blocks > 0:
            used_blocks = total_blocks - free_blocks
            util_pct = round(100.0 * used_blocks / total_blocks, 1)
        else:
            util_pct = 0.0

        mp_encoded = part.mount_point.replace('/', '_') or '_root'
        self.state_db.set(self.state_db.STATE_DB,
            f"SYSTEM_STORAGE_PARTITION|{mp_encoded}", {
                "device": part.device,
                "filesystem_type": part.fstype,
                "mount_point": part.mount_point,
                "utilization_percent": str(util_pct),
                "timestamp": iso_now()
        })
        parent_dev = self.get_parent_device(part.device)
        devices.setdefault(parent_dev, set()).add(part.device)

    for dev, parts in devices.items():
        self.state_db.set(self.state_db.STATE_DB,
            f"SYSTEM_STORAGE_DEVICE|{dev}", {
                "num_partitions": str(len(parts)),
                "type": self.detect_device_type(dev)
        })
```

##### 9.1.3 Threshold and Alarm Engine

```python
class AlarmManager:
    def __init__(self, log_func):
        self.log_func = log_func
        syslog.openlog(SYSLOG_IDENTIFIER, syslog.LOG_PID, syslog.LOG_DAEMON)

    def raise_alarm(self, alarm_type, resource_id, current_value, threshold):
        """
        Raise alarm:
          → syslog LOG_WARNING (structured message)
          → syslog LOG_ALERT   (human readable message)
        """
        # Human readable
        msg = (f"ALARM RAISED: {alarm_type} | "
               f"Resource: {resource_id} | "
               f"Current: {current_value}% | "
               f"Threshold: {threshold}%")
        self.log_func(msg)
        syslog.syslog(syslog.LOG_ALERT, msg)

        # Structured for parsing
        structured = (f"PLATFORM_ALARM: type={alarm_type}, "
                      f"resource={resource_id}, "
                      f"action=raised, "
                      f"current={current_value}, "
                      f"threshold={threshold}")
        syslog.syslog(syslog.LOG_WARNING, structured)

    def clear_alarm(self, alarm_type, resource_id, current_value, threshold):
        """
        Clear alarm:
          → syslog LOG_INFO (structured message)
          → syslog LOG_INFO (human readable message)
        """
        # Human readable
        msg = (f"ALARM CLEARED: {alarm_type} | "
               f"Resource: {resource_id} | "
               f"Current: {current_value}% | "
               f"Threshold: {threshold}%")
        self.log_func(msg)
        syslog.syslog(syslog.LOG_INFO, msg)

        # Structured for parsing
        structured = (f"PLATFORM_ALARM: type={alarm_type}, "
                      f"resource={resource_id}, "
                      f"action=cleared, "
                      f"current={current_value}, "
                      f"threshold={threshold}")
        syslog.syslog(syslog.LOG_INFO, structured)


class CPUMonitor:
    def _check_alarm(self, cpu_core):
        """
        --- Threshold Checks ---
        """
        try:
            key           = cpu_core.get_key()
            current_alarm = self.alarm_states.get(key, 'cleared')

            # threshold = 0 means disabled
            if self.threshold == 0:
                new_alarm = 'cleared'
            else:
                new_alarm = (
                    'active'
                    if cpu_core.current_utilization >= self.threshold
                    else 'cleared'
                )

            # Only act on state change
            if new_alarm != current_alarm:
                self.alarm_states[key] = new_alarm

                if new_alarm == 'active':
                    self.alarm_manager.raise_alarm(
                        'CPU_UTILIZATION',
                        key,
                        cpu_core.current_utilization,
                        self.threshold
                    )
                else:
                    self.alarm_manager.clear_alarm(
                        'CPU_UTILIZATION',
                        key,
                        cpu_core.current_utilization,
                        self.threshold
                    )

        except Exception as e:
            self.log_error(
                f"Failed to check alarm for {cpu_core.get_key()}: {str(e)}"
            )
```

##### 9.2.1 stormond (Storage Monitoring Daemon)

**Location:** `/usr/bin/stormond (part of PMON container)`
**Language:** Python 3
**Managed by:** supervisord within PMON container
**Dependencies:** `redis-server.service`, `database.service`

```
[Unit]
Description=SONiC Storage Monitoring Daemon
After=pmon.service
PartOf=pmon.service

[Service]
Type=simple
ExecStart=/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
Restart=no

[Install]
WantedBy=multi-user.target
```

**Initialization sequence:**

```
1.   Connect to CONFIG_DB and STATE_DB
2.   Load SRM configuration from STORAGE_GLOBAL|global
3.   Initialize legacy stormond components (storage device monitoring)
4.   Discover permanent storage devices and partitions from /proc/mounts
5.   Filter removable devices via /sys/block/*/removable
6.   Initialize alarm manager
7.   Enter main loop
```

**Main loop (simplified pseudocode):**

```python
class DaemonStorage(daemon_base.DaemonBase):
    def __init__(self, log_identifier):
        self.state_db = daemon_base.db_connect("STATE_DB")
        self.config_db = daemon_base.db_connect("CONFIG_DB")
        
        self.storage_table = swsscommon.Table(self.state_db, STORAGE_TABLE)
        self.device_table = swsscommon.Table(self.state_db, STORAGE_DEVICE_TABLE)
        
        self.partition_monitor = StoragePartitionMonitor(self.log)
        self.alarm_manager = AlarmManager(self.log)
        
        self._load_srm_config()
        self.srm_polling_interval = 5  # seconds

    def run(self):
        # Reload configuration
        self._load_srm_config()
        
        # Legacy stormond: Update device info
        self.get_dynamic_fields_update_state_db()
        
        # SRM: Update partition utilization and alarms
        self.update_srm_storage_partition_info()
        
        # Wait for next cycle
        if self.stop_event.wait(self.srm_polling_interval):
            return False  # Exit requested
        
        # Sync FSIO stats to disk periodically (legacy)
        elapsed_time = time.time() - self.fsio_sync_time
        if elapsed_time > self.fsstats_sync_interval:
            self.sync_fsio_rw_json()
            self.write_sync_time_statedb()
        
        return True
```

##### 9.2.1.1 Storage Partition Discovery and Monitoring

**Partition Discovery:**

```python
class StoragePartitionMonitor:
    def _parse_proc_mounts(self):
        """Parse /proc/mounts for mounted filesystems."""
        mount_entries = []
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 4:
                    device, mount_point, fstype, options = parts[0], parts[1], parts[2], parts[3]
                    mount_entries.append({
                        'device': device,
                        'mount_point': mount_point,
                        'fstype': fstype,
                        'options': options
                    })
        return mount_entries

    def _discover_permanent_storage(self):
        """Discover permanently attached storage devices."""
        mount_entries = self._parse_proc_mounts()
        
        for entry in mount_entries:
            device = entry['device']
            mount_point = entry['mount_point']
            fstype = entry['fstype']
            
            # Skip non-block devices
            if not device.startswith('/dev/'):
                continue
            
            # Skip excluded filesystem types
            if fstype in EXCLUDED_MOUNT_TYPES:
                continue
            
            # Skip excluded mount points
            if any(mount_point.startswith(excluded) for excluded in EXCLUDED_MOUNT_POINTS):
                continue
            
            # Extract base device name (sda, nvme0n1, mmcblk0)
            device_name = self._extract_device_name(device)
            
            # Check if permanent storage
            if not self._is_permanent_storage(device_name):
                continue
            
            # Check if removable
            if self._is_removable_device(device_name):
                continue
            
            # Add to permanent_devices dictionary
            # ...
```
**Utilization Collection:**

```python
def get_partition_utilization(self):
    """Get utilization for all mounted partitions."""
    utilization_data = {}
    
    for device_name, device_info in self.permanent_devices.items():
        for partition in device_info['partitions']:
            partition_path = partition['partition']
            mount_point = partition['mount_point']
            
            try:
                # Use os.statvfs() system call
                stat = os.statvfs(mount_point)
                
                total_blocks = stat.f_blocks
                free_blocks = stat.f_bfree
                available_blocks = stat.f_bavail
                used_blocks = total_blocks - free_blocks
                block_size = stat.f_frsize
                
                # Validate for negative values (corrupted metadata)
                if total_blocks < 0 or free_blocks < 0 or available_blocks < 0 or \
                   used_blocks < 0 or block_size < 0:
                    raise ValueError(f"Negative value detected: ...")
                
                # Calculate sizes in bytes
                total_bytes = total_blocks * block_size
                used_bytes = used_blocks * block_size
                available_bytes = available_blocks * block_size
                
                # Calculate utilization percentage
                if total_blocks > 0:
                    utilization_percent = (used_blocks / total_blocks) * 100
                else:
                    utilization_percent = 0.0
                
                # Store partition data
                utilization_data[device_name][partition_path] = {
                    'device_name': device_name,
                    'partition_name': partition_path,
                    'mount_point': mount_point,
                    'fstype': partition['fstype'],
                    'total_memory': str(total_bytes),
                    'used_memory': str(used_bytes),
                    'available_memory': str(available_bytes),
                    'storage_utilization': str(round(utilization_percent, 2))
                }
                
            except ValueError as e:
                # Corrupted filesystem metadata
                self.log.log_error(f"Corrupted filesystem metadata for {partition_path}: {str(e)}")
                continue
                
            except OSError as e:
                # Mount point disappeared, permission denied, etc.
                self.log.log_warning(f"Failed to access {partition_path}: {str(e)}")
                continue
    
    return utilization_data
```

##### 9.2.1.2 Threshold and Alarm Engine

```python
class AlarmManager:
    ALARM_ACTIVE = "active"
    ALARM_CLEARED = "cleared"
    
    def __init__(self, logger):
        self.log = logger
        self.active_alarms = {}  # resource_id -> alarm_info
        syslog.openlog(SYSLOG_IDENTIFIER, syslog.LOG_PID, syslog.LOG_DAEMON)
    
    def check_threshold(self, resource_id, current_value, threshold, resource_type="storage"):
        """
        Check if threshold exceeded and manage alarm state.
        Returns: "active" or "cleared"
        """
        try:
            current_val = float(current_value)
            threshold_val = float(threshold)
            
            # Check if threshold exceeded
            if current_val > threshold_val:
                # Generate or maintain active alarm
                if resource_id not in self.active_alarms:
                    alarm_msg = (
                        f"{resource_type.upper()} ALARM ACTIVE: {resource_id} "
                        f"utilization {current_val}% exceeds threshold {threshold_val}%"
                    )
                    self.log.log_warning(alarm_msg)
                    syslog.syslog(syslog.LOG_WARNING, alarm_msg)
                    
                    self.active_alarms[resource_id] = {
                        'timestamp': time.time(),
                        'value': current_val,
                        'threshold': threshold_val
                    }
                
                return self.ALARM_ACTIVE
            
            else:
                # Clear alarm if previously active
                if resource_id in self.active_alarms:
                    clear_msg = (
                        f"{resource_type.upper()} ALARM CLEARED: {resource_id} "
                        f"utilization {current_val}% is below threshold {threshold_val}%"
                    )
                    self.log.log_notice(clear_msg)
                    syslog.syslog(syslog.LOG_INFO, clear_msg)
                    del self.active_alarms[resource_id]
                
                return self.ALARM_CLEARED
        
        except (ValueError, TypeError) as e:
            self.log.log_error(f"Invalid threshold comparison for {resource_id}: {str(e)}")
            return self.ALARM_CLEARED

def update_srm_storage_partition_info(self):
    """Update partition info and check thresholds."""
    utilization_data = self.partition_monitor.get_partition_utilization()
    
    for base_device, device_data in utilization_data.items():
        for partition_path, partition_data in device_data['partitions'].items():
            
            storage_utilization = float(partition_data['storage_utilization'])
            resource_id = f"{base_device}|{partition_path}"
            
            # Check threshold and get alarm status
            alarm_status = self.alarm_manager.check_threshold(
                resource_id=resource_id,
                current_value=storage_utilization,
                threshold=self.storage_utilization_threshold,
                resource_type="storage"
            )
            
            # Update STATE_DB with partition data and alarm status
            partition_key = f"{base_device}|{partition_path}"
            fvp = swsscommon.FieldValuePairs([
                ("device_name", base_device),
                ("partition_name", partition_path),
                ("mount_point", partition_data['mount_point']),
                ("fstype", partition_data['fstype']),
                ("total_memory", partition_data['total_memory']),
                ("used_memory", partition_data['used_memory']),
                ("available_memory", partition_data['available_memory']),
                ("storage_utilization", partition_data['storage_utilization']),
                ("alarm_status", alarm_status),
                ("timestamp", str(self.get_formatted_time(time.time())))
            ])
            self.storage_table.set(partition_key, fvp)
```

#### 9.2 Switch State Service Design

No changes to `orchagent` or other `swss` components. This feature is entirely within the management/platform plane.

#### 9.3 SyncD

No changes to `syncd`.

#### 9.4 CLI

#### 9.4.1 Configuration Commands

**CPU / Memory History Configuration:**

```

sudo config platform cpu-history measurement-interval <1-10>
sudo config platform cpu-history duration <30-180>
sudo config platform cpu-history status <enable or disable>
sudo config platform ram-history measurement-interval <1-10> 
sudo config platform ram-history duration <30-180>
sudo config platform ram-history status <enable or disable>
```

| Parameter             | Range             | Default | Unit    |
|-----------------------|-------------------|---------|---------|
| `measurement-interval`| 1–10              | 5       | minutes |
| `duration`            | 30–180            | 60      | minutes |
| `status`              | enable or disable | disable |    -    |

Validation: `duration` must be an integer and should be in given `range`. If not, CLI rejects with error.

**Threshold Configuration:**

```
sudo config platform cpu utilization-threshold <0-100>
sudo config platform ram utilization-threshold <0-100>
sudo config platform storage utilization-threshold <0-100>
```

Example:
```
admin@sonic:~$ sudo config platform cpu utilization-threshold 60
CPU utilization threshold set to 60%.
```

#### 9.4.2 Show Commands

**Show CPU Utilization (Current-snapshot):**

```
admin@sonic:~$ show platform cpu
```

Output:
```
  Cpu Index    Core Index  Utilization    Alarm Status    Threshold    Timestamp
-----------  ------------  -------------  --------------  -----------  ------------------
          0             0  11%            Cleared         60%          20260602 14:51:07Z
          0             1  5%             Cleared         60%          20260602 14:51:07Z

```

**Show CPU Utilization History:**

```
admin@sonic:~$ show platform cpu-history-status
```

Output:
```
  Status : Enabled
```

```
admin@sonic:~$ show platform cpu-history
```

Output:
```
    Status   : Enabled
  Duration : 60 minutes
  Interval : 5 minutes

 Cpu Index    Core Index       Timestamp        Utilization
-----------  ------------  ------------------  -------------
     0            0        20260603 04:03:46Z       5%
     0            0        20260603 04:08:46Z       5%
     0            0        20260603 04:13:46Z       5%
     0            0        20260603 04:18:46Z       5%
     0            0        20260603 04:23:46Z       5%
```

**Show Memory Utilization (Current-snapshot):**

```
admin@sonic:~$ show platform ram
```

Output:
```
 Total Memory    Used Memory    Available    Utilization    Alarm Status    Threshold       Timestamp
--------------  -------------  -----------  -------------  --------------  -----------  ------------------
  3945556 KB     1738704 KB    2206852 KB        44%          Cleared          80%      20260602 14:51:12Z
```

**Show Memory Utilization History:**

```
admin@sonic:~$ show platform ram-history-status
```

Output:
```
 Status : Enabled
```

```
admin@sonic:~$ show platform ram-history
```

Output:
```
  Status   : Enabled
  Duration : 60 minutes
  Interval : 5 minutes

    Timestamp        Total Memory    Used Memory    Available    Utilization
------------------  --------------  -------------  -----------  -------------
20260603 04:03:51Z    3945556 KB     1758676 KB    2186879 KB        44%
20260603 04:08:51Z    3945556 KB     1764160 KB    2181395 KB        44%
20260603 04:13:51Z    3945556 KB     1759789 KB    2185766 KB        44%
20260603 04:18:51Z    3945556 KB     1760426 KB    2185129 KB        44%
20260603 04:23:51Z    3945556 KB     1761242 KB    2184313 KB        44%
```

**Show Storage Utilization:**

```
admin@sonic:~$ show platform storage
```

Output:
```
 Device    Partition      Total        Used      Available    Utilization    Alarm Status    Threshold       Timestamp
--------  -----------  -----------  ----------  -----------  -------------  --------------  -----------  ------------------
  sda      /dev/sda3   16206120 KB  6897984 KB  9291752 KB      42.56%         Cleared          75%      20260602 14:50:55Z
```

**Show Active Alarms:**

```
admin@sonic:~$ show platform cpu
```

Output:
```
  Cpu Index    Core Index  Utilization    Alarm Status    Threshold    Timestamp
-----------  ------------  -------------  --------------  -----------  ------------------
          0             0  90%            Active          85%          20260603 05:15:47Z
          0             1  7%             Cleared         85%          20260603 05:15:47Z
```

```
admin@sonic:~$ show platform ram
```

Output:
```
 Total Memory    Used Memory    Available    Utilization    Alarm Status    Threshold       Timestamp
--------------  -------------  -----------  -------------  --------------  -----------  ------------------
  3945556 KB     3732208 KB     213348 KB        95%           Active          80%      20260603 05:19:37Z
```

```
admin@sonic:~$ show platform storage
```

Output:
```
 Device    Partition      Total        Used       Available    Utilization    Alarm Status    Threshold       Timestamp
--------  -----------  -----------  -----------  -----------  -------------  --------------  -----------  ------------------
  sda      /dev/sda3   16206120 KB  12645768 KB  3543968 KB      78.03%          Active          75%      20260603 05:23:10Z
```

**Show Running Configuration:**

```
admin@sonic:~$ show runningconfiguration all | grep cpu
```

Output:
```
            "cpu_history_duration": "60",
            "cpu_history_measurement_interval": "5",
            "cpu_utilization_threshold": "60",
```

```
admin@sonic:~$ show runningconfiguration all | grep ram
```

Output:
```
            "ram_history_duration": "60",
            "ram_history_measurement_interval": "5",
            "ram_utilization_threshold": "80"
```

```
admin@sonic:~$ show runningconfiguration all | grep storage
```

Output:
```
            "storage_utilization_threshold": "75"
```


### 9.5 REST API Support

Not Scoped
```

### 9.6 gNMI Support

Not Scoped
```

### 9.7 YANG Model

**sonic-platform.yang**

```yang:src/sonic-yang-models/yang-models/sonic-platform.yang
module sonic-platform {
    yang-version 1.1;
    namespace "http://github.com/sonic-net/sonic-platform";
    prefix splat;

    import ietf-yang-types {
        prefix yang;
    }

    organization
        "SONiC";

    contact
        "SONiC Community
         https://sonic-net.github.io/SONiC/";

    description  
        "YANG model for SONiC platform resource monitoring including
         CPU, RAM, and Storage utilization tracking with historical
         data retention and threshold-based alarming capabilities.
         This module provides comprehensive monitoring of system
         resources with configurable thresholds and history retention.";

    revision 2026-05-14 {
        description
            "Initial revision for System Resource Monitoring (SRM).";
        reference
            "RFC 7950: The YANG 1.1 Data Modeling Language
             RFC 6991: Common YANG Data Types";
    }

    // ========================================================================
    // TYPEDEFS
    // ========================================================================
    typedef percentage {
        type uint8 {
            range "0..100";
        }
        description 
            "Percentage value ranging from 0 to 100.";
    }
    typedef enable-state {
        type enumeration {
            enum enabled {
                description
                    "Feature is enabled.";
            }
            enum disabled {
                description
                    "Feature is disabled.";
            }
        }
        description 
            "Administrative state for enabling or disabling a feature.";
    }
    typedef alarm-status {
        type enumeration {
            enum active {
                description
                    "Alarm condition is currently active.";
            }
            enum cleared {
                description
                    "Alarm condition has been cleared.";
            }
        }
        description 
            "Operational status of an alarm condition.";
    }

    // ========================================================================
    // TOP-LEVEL CONTAINER
    // ========================================================================
    container sonic-platform {
        description 
            "Top-level container for SONiC platform resource monitoring
             including CPU, RAM, and storage subsystems.";

        // ====================================================================
        // CPU_GLOBAL - Global CPU Configuration
        // ====================================================================
        container CPU_GLOBAL {
            description
                "Global CPU monitoring configuration container.
                 Contains system-wide CPU monitoring parameters including
                 history collection settings and alarm thresholds.";
            list CPU_GLOBAL_LIST {
                key "global";
                description 
                    "List containing global CPU monitoring configuration.
                     Typically contains a single entry with key 'global'.";
                // Key
                leaf global {
                    type string {
                        pattern "global";
                    }
                    description
                        "Key identifier for global CPU configuration.
                         Must be the literal string 'global'.";
                }
                // Configuration fields (RW)
                leaf cpu_history_measurement_interval {
                    type uint32 {
                        range "1..10";
                    }
                    units "minutes";
                    default "5";
                    description
                        "Interval at which CPU utilization history measurements
                         are collected and recorded. Valid range: 1-10 minutes.";
                }
                leaf cpu_history_duration {
                    type uint32 {
                        range "30..180";
                    }
                    units "minutes";
                    default "60";
                    description
                        "Duration for retaining CPU utilization history data.
                         History older than this duration will be purged.
                         Valid range: 30-180 minutes.";
                }
                leaf history_status {
                    type enable-state;
                    default "disabled";
                    description 
                        "Enable or disable CPU history collection.
                         When disabled, no historical data is collected.";
                }
                leaf cpu_utilization_threshold {
                    type percentage;
                    default "85";
                    description 
                        "Threshold percentage for CPU utilization alarming.
                         When CPU utilization exceeds this threshold, an alarm
                         is raised. Valid range: 0-100%.";
                }
            }
        }

        // ====================================================================
        // CPU_TABLE - Current CPU Utilization Data
        // ====================================================================
        container CPU_TABLE {
            description 
                "Current CPU utilization data per CPU core.
                 Contains real-time operational state for each CPU core
                 in the system.";
            list CPU_TABLE_LIST {
                key "cpu_index cpu_core_index";
                config false;
                description
                    "List of CPU cores with current utilization metrics.
                     All fields are read-only operational data populated
                     from STATE_DB.";
                // Keys
                leaf cpu_index {
                    type uint32;
                    description 
                        "Index of the CPU package or socket.
                         Identifies the physical CPU in multi-socket systems.";
                }
                leaf cpu_core_index {
                    type uint32;
                    description
                        "Index of the CPU core within the package.
                         Identifies individual cores within a CPU socket.";
                }
                // Operational/State fields (RO)
                leaf cpu_utilization {
                    type percentage;
                    description
                        "Current CPU utilization percentage for this core.
                         Represents the percentage of time the core is busy.";
                }
                leaf alarm_status {
                    type alarm-status;
                    description
                        "Alarm status indicating whether CPU utilization
                         has exceeded the configured threshold.";
                }
                leaf timestamp {
                    type yang:date-and-time;
                    description
                        "Timestamp when this CPU utilization measurement
                         was recorded.";
                    reference
                        "RFC 6991: Common YANG Data Types";
                }
            }
        }

        // ====================================================================
        // CPU_HISTORY_TABLE - Historical CPU Utilization Data
        // ====================================================================
        container CPU_HISTORY_TABLE {
            description
                "Historical CPU utilization data for trend analysis.
                 Contains time-series data for CPU utilization per core.";
            list CPU_HISTORY_TABLE_LIST {
                key "cpu_index cpu_core_index timestamp";
                config false;
                description
                    "List of historical CPU utilization records.
                     All fields are read-only operational data populated
                     from STATE_DB. Records are retained according to
                     cpu_history_duration configuration.";
                // Keys
                leaf cpu_index {
                    type uint32;
                    description 
                        "Index of the CPU package or socket.";
                }
                leaf cpu_core_index {
                    type uint32;
                    description
                        "Index of the CPU core within the package.";
                }
                leaf timestamp {
                    type yang:date-and-time;
                    description
                        "Timestamp of this historical measurement record.
                         Forms part of the composite key for uniqueness.";
                    reference 
                        "RFC 6991: Common YANG Data Types";
                }
                // Operational/State fields (RO)
                leaf cpu_history_utilization {
                    type percentage;
                    description 
                        "Historical CPU utilization percentage recorded
                         at the specified timestamp.";
                }
            }
        }

        // ====================================================================
        // RAM_GLOBAL - Global RAM Configuration and Status
        // ====================================================================
        container RAM_GLOBAL {
            description
                "Global RAM monitoring configuration and current status.
                 Contains system-wide memory monitoring parameters and
                 real-time memory utilization data.";
            list RAM_GLOBAL_LIST {
                key "global";
                description
                    "List containing global RAM monitoring configuration
                     and operational status. Typically contains a single
                     entry with key 'global'.";
                // Key
                leaf global {
                    type string {
                        pattern "global";
                    }
                    description 
                        "Key identifier for global RAM configuration.
                         Must be the literal string 'global'.";
                }
                // Configuration fields (RW)
                leaf ram_history_measurement_interval {
                    type uint32 {
                        range "1..10";
                    }
                    units "minutes";
                    default "5";
                    description
                        "Interval at which RAM utilization history measurements
                         are collected and recorded. Valid range: 1-10 minutes.";
                }
                leaf ram_history_duration {
                    type uint32 {
                        range "30..180";
                    }
                    units "minutes";
                    default "60";
                    description
                        "Duration for retaining RAM utilization history data.
                         History older than this duration will be purged.
                         Valid range: 30-180 minutes.";
                }
                leaf history_status {
                    type enable-state;
                    default "disabled";
                    description
                        "Enable or disable RAM history collection.
                         When disabled, no historical data is collected.";
                }
                leaf ram_utilization_threshold {
                    type percentage;
                    default "80";
                    description
                        "Threshold percentage for RAM utilization alarming.
                         When memory utilization exceeds this threshold,
                         an alarm is raised. Valid range: 0-100%.";
                }
                // Operational/State fields (RO)
                leaf total_memory {
                    type uint64;
                    units "bytes";
                    config false;
                    description
                        "Total system memory capacity in bytes.
                         Represents the physical RAM installed.";
                }
                leaf used_memory {
                    type uint64;
                    units "bytes";
                    config false;
                    description
                        "Currently used memory in bytes.
                         Includes memory used by applications, kernel,
                         and buffers/cache.";
                }
                leaf available_memory {
                    type uint64;
                    units "bytes";
                    config false;
                    description
                        "Available memory in bytes.
                         Memory that can be allocated without swapping.";
                }
                leaf memory_utilization {
                    type percentage;
                    config false;
                    description
                        "Current memory utilization percentage.
                         Calculated as (used_memory / total_memory) * 100.";
                }
                leaf alarm_status {
                    type alarm-status;
                    config false;
                    description
                        "Alarm status indicating whether memory utilization
                         has exceeded the configured threshold.";
                }
                leaf timestamp {
                    type yang:date-and-time;
                    config false;
                    description
                        "Timestamp of the current memory measurement.";
                    reference
                        "RFC 6991: Common YANG Data Types";
                }
            }
        }

        // ====================================================================
        // RAM_HISTORY_TABLE - Historical RAM Utilization Data
        // ====================================================================
        container RAM_HISTORY_TABLE {
            description
                "Historical RAM utilization data for trend analysis.
                 Contains time-series data for system memory utilization.";
            list RAM_HISTORY_TABLE_LIST {
                key "timestamp";
                config false;
                description
                    "List of historical RAM utilization records.
                     All fields are read-only operational data populated
                     from STATE_DB. Records are retained according to
                     ram_history_duration configuration.";
                // Key
                leaf timestamp {
                    type yang:date-and-time;
                    description
                        "Timestamp of this historical measurement record.
                         Serves as the unique key for each history entry.";
                    reference
                        "RFC 6991: Common YANG Data Types";
                }
                // Operational/State fields (RO)
                leaf total_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Total system memory at the time of measurement.";
                }
                leaf used_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Used memory at the time of measurement.";
                }
                leaf available_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Available memory at the time of measurement.";
                }
                leaf memory_utilization {
                    type percentage;
                    description
                        "Memory utilization percentage recorded at the
                         specified timestamp.";
                }
            }
        }

        // ====================================================================
        // STORAGE_GLOBAL - Global Storage Configuration
        // ====================================================================
        container STORAGE_GLOBAL {
            description
                "Global storage monitoring configuration container.
                 Contains system-wide storage monitoring parameters.";
            list STORAGE_GLOBAL_LIST {
                key "global";
                description
                    "List containing global storage monitoring configuration.
                     Typically contains a single entry with key 'global'.";
                // Key
                leaf global {
                    type string {
                        pattern "global";
                    }
                    description
                        "Key identifier for global storage configuration.
                         Must be the literal string 'global'.";
                }
                // Configuration field (RW)
                leaf storage_utilization_threshold {
                    type percentage;
                    default "75";
                    description
                        "Threshold percentage for storage utilization alarming.
                         When storage utilization exceeds this threshold,
                         an alarm is raised. Valid range: 0-100%.";
                }
            }
        }

        // ====================================================================
        // STORAGE_TABLE - Current Storage Utilization Data
        // ====================================================================
        container STORAGE_TABLE {
            description
                "Current storage utilization data per device and partition.
                 Contains real-time operational state for all storage
                 devices and their partitions.";
            list STORAGE_TABLE_LIST {
                key "device_name partition_name";
                config false;
                description
                    "List of storage devices and partitions with current
                     utilization metrics. All fields are read-only
                     operational data populated from STATE_DB.";
                // Keys
                leaf device_name {
                    type string;
                    description
                        "Name of the storage device.
                         Examples: sda, nvme0n1, mmcblk0.";
                }
                leaf partition_name {
                    type string;
                    description
                        "Name of the partition on the device.
                         Examples: sda1, nvme0n1p1, mmcblk0p1.";
                }
                // Operational/State fields (RO)
                leaf total_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Total storage capacity of the partition in bytes.
                         Represents the formatted capacity.";
                }
                leaf used_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Used storage space in bytes.
                         Includes all files and metadata.";
                }
                leaf available_memory {
                    type uint64;
                    units "bytes";
                    description
                        "Available storage space in bytes.
                         Space that can be used for new files.";
                }
                leaf storage_utilization {
                    type percentage;
                    description
                        "Storage utilization percentage.
                         Calculated as (used_memory / total_memory) * 100.";
                }
                leaf alarm_status {
                    type alarm-status;
                    description
                        "Alarm status indicating whether storage utilization
                         has exceeded the configured threshold.";
                }
                leaf timestamp {
                    type yang:date-and-time;
                    description
                        "Timestamp when this storage measurement was recorded.";
                    reference
                        "RFC 6991: Common YANG Data Types";
                }
            }
        }
    }
}
```

### 9.8 Error Handling

This section describes error handling organized by subsystem, with precise handling descriptions.

####9.8.1 Database Connection Errors

|Scenario                               |Handling                    |Log Level  |
|---------------------------------------|----------------------------|--------- -|
|Database connection failure (startup)  |Exit, supervisord restarts  |ERROR      |
|STATE_DB write failure                 |Skip, retry next cycle (5s) |WARNING    |

---

#### 9.8.2 Data Collection Errors

|Error Condition                           |Handling                                      |Log Level |
|------------------------------------------|----------------------------------------------|----------|
|/proc/mounts read error                   |Skip discovery, retry next cycle              |ERROR     |
|Malformed /proc/mounts line               |Skip line, continue parsing                   |Silent    |
|/sys/block/*/removable error              |Assume permanent device, continue             |WARNING   |
|Mount point disappeared |PermissionError  |Skip partition, retry next cycle              |WARNING   |
|statvfs() negative values                 |Skip partition, retry next cycle              |ERROR     |
|statvfs() permission denied               |Skip partition, retry next cycle              |WARNING   |
|Zero total blocks                         |Set utilization 0%, continue                  |INFO      |
|Partition mounted during operation        |Rediscover on next cycle, add to STATE_DB     |INFO      |
|Partition unmounted during operation      |Remove from STATE_DB, clear alarms if active  |NOTICE    |


#### 9.8.3 Configuration Errors

|Error Condition                       |Handling                                               |Log Level |
|--------------------------------------|-------------------------------------------------------|----------|
|STORAGE_GLOBAL missing at startup     |Create default config (75% threshold)                  |INFO      |
|Invalid threshold value               |Use default (75%)                                      |WARNING   |
|Threshold out of range                |Clamp to 0-100                                         |WARNING   |
|Threshold changed while alarm active  |Re-evaluate immediately, clear if below new threshold  |INFO      |

#### 9.8.4 Alarm Processing Errors

|Error Condition                       |Handling                            |Log Level |
|--------------------------------------|------------------------------------|----------|
|Invalid alarm values (non-numeric)    |Return "cleared", skip check        |ERROR     |
|Syslog write failure                  |Continue (alarm still in STATE_DB)  |Silent    |
|Multiple partitions exceed threshold  |Raise separate alarm per partition  |WARNING   |

#### 9.8.5 Legacy Stormond Integration Errors

|Error Condition          |Handling                             |Log Level |
|-------------------------|------------------------------------ |----------|
|FSIO JSON read failure   |Use STATE_DB baseline or init state  |NOTICE    |
|FSIO JSON parse error    |Use STATE_DB baseline or init state) |ERROR     |
|FSIO JSON write failure  |Skip sync, retry next interval       |WARNING   |
|STORAGE_INFO corruption  |Pivot to JSON baseline if available  |WARNING   |

#### 9.8.6 Daemon Lifecycle Errors

|Error Condition                  |Handling                            |Log Level |
|---------------------------------|------------------------------------|----------|
|SIGTERM/SIGINT received          |Sync FSIO, clean exit               |NOTICE    |
|Uncaught exception in main loop  |Exit non-zero, supervisord restarts |ERROR     |
|Daemon crash                     |Supervisord restarts after 30s      |N/A       |

#### 9.8.7  Infrastructure Errors

|Error Condition                     |Handling                                        |Log Level |
|------------------------------------|------------------------------------------------|----------|
|STATE_DB unreachable during runtime |Continue monitoring, retry writes next cycle    |ERROR     |
|Disk full (STATE_DB writes fail)    |Continue read-only, resume when space available |ERROR     |
|STATE_DB entries manually deleted   |Re-create on next cycle (5s)                    |N/A       |


#### 9.8.6 CLI, REST, and gNMI Errors
Scenario    Handling
show system-resource cpu issued before daemon has completed first collection cycle    STATE_DB contains no SYSTEM_CPU_UTILIZATION entries. CLI displays: "No CPU utilization data available. The monitoring daemon may still be initializing." REST API returns HTTP 503 Service Unavailable with a JSON body: {"error": "Data not yet available. Retry after a few seconds."}
show system-resource cpu history with no history entries collected yet    CLI displays: "No CPU history data available. History collection interval is <X> minutes; please wait for the first sample." REST API returns HTTP 200 with an empty list: {"cpu_history": []}.
show system-resource storage when no permanent partitions are discovered    CLI displays: "No storage partitions found." Log LOG_WARNING — this is unexpected on any real system and may indicate a /proc/mounts parsing issue.
config system-resource threshold cpu <value> with out-of-range value (e.g., 0 or 101)    YANG range "1..100" constraint rejects the value. CLI returns: "Error: Invalid value <value>. CPU threshold must be between 1 and 100." CONFIG_DB is not modified.
config system-resource history cpu interval <value> where value does not evenly divide duration    YANG must constraint rejects the value. CLI returns: "Error: Interval <value> does not evenly divide duration <duration>. Valid intervals for duration=<duration>: <list>." CONFIG_DB is not modified.
REST API PATCH with malformed JSON body    Management framework returns HTTP 400 Bad Request with a descriptive error: {"error": "Malformed JSON: <parser error details>"}. CONFIG_DB is not modified.
REST API PATCH with valid JSON but invalid field values    YANG validation rejects the request. Management framework returns HTTP 400 Bad Request: {"error": "Validation failed: <constraint violation details>"}.
REST API GET for a resource that exists in YANG but has no STATE_DB data    Returns HTTP 200 with empty or default-valued response body (per OpenAPI schema). Does not return 404 — the resource path is valid; only the data is absent.
gNMI Subscribe (STREAM mode) for CPU utilization — daemon stops publishing    gNMI server detects that STATE_DB timestamp has not updated beyond the expected cycle interval (10 s + tolerance). The server continues to hold the subscription open but does not send stale updates. When data resumes, streaming resumes automatically.
gNMI Set with invalid configuration values    YANG validation rejects the request. gNMI server returns INVALID_ARGUMENT status code with a description of the constraint violation.
Concurrent CLI/REST configuration writes to the same table    CONFIG_DB uses Redis atomic operations. The last write wins. Each write independently triggers the daemon's CONFIG_DB subscription callback, which re-reads the full configuration. No locking is required. A LOG_INFO message is emitted for each configuration change processed.
sonic-clear system-resource history cpu when history is already empty    Command succeeds silently (idempotent). CLI displays: "CPU history cleared." No error is raised.
sonic-clear system-resource alarms when no alarms exist

#### 9.8.7 Race Conditions and Concurrency
Scenario    Handling
CONFIG_DB subscription callback fires during an active collection cycle    The callback sets an in-memory flag (config_changed = True). The daemon checks this flag at the end of the current collection cycle (after STATE_DB writes are complete) and applies the new configuration before the next cycle begins. This avoids mid-cycle configuration changes that could produce inconsistent data.
Multiple CONFIG_DB changes arrive in rapid succession (e.g., operator sets threshold and interval within the same second)    Each change triggers a separate subscription callback. The daemon coalesces changes by reading the entire configuration from CONFIG_DB when it processes the config_changed flag, rather than applying individual deltas. This ensures the final applied state matches CONFIG_DB regardless of callback ordering.
STATE_DB read by CLI/REST occurs simultaneously with daemon write    Redis commands are atomic. A HGETALL by the CLI will return either the previous complete snapshot or the new complete snapshot — never a partial mix. No application-level locking is needed. The daemon uses HMSET (single atomic write per key) to update all fields of a hash simultaneously.
History write and history read (show ... history) occur simultaneously    The daemon writes history entries as individual Redis hash keys (`SYSTEM_CPU_UTILIZATION_HISTORY
Daemon restarts while CLI is reading STATE_DB    The CLI may read stale data that is about to be cleared. After the daemon restart completes (clears and repopulates STATE_DB), subsequent CLI reads return fresh data. No crash or corruption occurs on the CLI side — it simply displays whatever STATE_DB contains at read time.
Alarm evaluation and threshold configuration change occur simultaneously    The daemon processes configuration changes and alarm evaluation sequentially within the same thread. There is no concurrent execution — the daemon is single-threaded with an event loop. Configuration is applied first, then the next alarm evaluation uses the updated threshold.

#### 9.8.8 Error Recovery Summary
The following diagram illustrates the daemon's error recovery state machine:

                    ┌─────────────┐
                    │   STARTUP   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐    CONFIG_DB          ┌──────────────┐
                    │  INIT_DB    │───unreachable────────►│ WAIT_RETRY   │
                    │ CONNECTIONS │◄──────────────────────│ (exp backoff)│
                    └──────┬──────┘    connected          └──────────────┘
                           │
                    ┌──────▼──────┐
                    │  CLEAR      │  Clear *_HISTORY,
                    │  STALE DATA │  SYSTEM_RESOURCE_ALARM
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  READ       │
                    │  CONFIG     │  Read CONFIG_DB or use defaults
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │     MAIN LOOP           │◄──────────────────┐
              │  (every ~10 seconds)    │                   │
              └────────────┬────────────┘                   │
                           │                                │
              ┌────────────▼────────────┐                   │
              │  COLLECT DATA           │                   │
              │  /proc/stat, meminfo,   │                   │
              │  statvfs()              │                   │
              └────────────┬────────────┘                   │
                           │                                │
                     ┌─────▼─────┐                          │
                     │ Success?  │──── No ──► Log error,    │
                     └─────┬─────┘           skip resource, │
                           │ Yes             retain last ───┘
              ┌────────────▼────────────┐                   │
              │  WRITE STATE_DB         │                   │
              └────────────┬────────────┘                   │
                           │                                │
                     ┌─────▼─────┐                          │
                     │ DB write  │──── No ──► Log error,    │
                     │ success?  │           retry next ────┘
                     └─────┬─────┘           cycle
                           │ Yes
              ┌────────────▼────────────┐
              │  EVALUATE THRESHOLDS    │
              │  Raise / clear alarms   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  CHECK config_changed   │
              │  flag                   │───-─ Yes ──► Re-read config,
              └────────────┬────────────┘              reset buffers
                           │ No                        if needed
                           │◄──────────────────────────┘
              ┌────────────▼────────────┐
              │  SLEEP until next cycle │
              └────────────┬────────────┘
                           │
                           └──────────────────────────────► MAIN LOOP



#### 9.8.9 Error Code Reference
All errors returned by the CLI and REST API follow a consistent format. The table below catalogues every error code used by this feature:

|Error Code              |HTTP |Message                        |Trigger                              |
|------------------------|-------------------------------------|-------------------------------------|
|ERR_DAEMON_UNAVAILABLE  |503  |Daemon not running or no data  |STATE_DB empty, daemon not detected  |
|ERR_INVALID_THRESHOLD   |400  |Invalid threshold (0-100)      |YANG constraint violation            |
|ERR_CONFIG_NOT_FOUND    |404  |Config missing, using default  |STORAGE_GLOBAL missing               |
|ERR_INTERNAL            |500  |Internal error, check logs     |Unexpected exception                 |

#### 9.8.10 Syslog Error Message Catalog
All error and warning syslog messages emitted by system-resource-monitord are catalogued below for operational reference:


|Message ID   |Severity  |Message                                        |Condition                              |
|----------- -|----------------------------------------------------------|---------------------------------------|
|STORMON-001  |ERR       |Failed to parse /proc/mounts                   |/proc/mounts read failure              |
|STORMON-002  |ERR       |Corrupted filesystem metadata for <partition>  |Negative statvfs() values detected     |
|STORMON-003  |ERR       |Failed to initialize databases                 |CONFIG_DB/STATE_DB connection failure  |
|STORMON-004  |WARN      |STORAGE ALARM ACTIVE: <id> <X>% > <Y>%         |Partition exceeds threshold            |
|STORMON-005  |INFO      |STORAGE ALARM CLEARED: <id> <X>% < <Y>%        |Partition below threshold              |

### 9.9 Serviceability and Debug

#### 9.9.1 Logging

All daemon operations are logged via Python `syslog` module with facility `LOG_USER`.

| Log Level     | Usage                                                                   |
|---------------|-------------------------------------------------------------------------|
| `LOG_ERR`     | Unrecoverable errors — cannot read `/proc/stat`, STATE_DB write failure |
| `LOG_WARNING` | Threshold alarm raised, platform API failure, partition read failure    |
| `LOG_NOTICE`  | Threshold alarm cleared, configuration change applied                   |
| `LOG_INFO`    | Daemon start/stop, history buffer reset, partition discovery            |
| `LOG_DEBUG`   | Per-cycle collection details (disabled by default)                      |

Debug logging can be enabled at runtime:

```bash
sudo sonic-cli -c "debug system-resource-monitor verbose"
```

Or by setting an environment variable:

```bash
sudo systemctl set-environment SYSRESMON_LOG_LEVEL=DEBUG
sudo systemctl restart system-resource-monitord
```

#### 9.9.2 Techsupport Integration

The `show techsupport` command shall be extended to collect:

| Artifact          | Source                                                               |
|-------------------|----------------------------------------------------------------------|
| Daemon log        | `grep platformd /var/log/syslog`                                     |
| CONFIG_DB tables  | `CPU_GLOBAL, RAM_GLOBAL`,                                            |
| STATE_DB tables   | `CPU_TABLE`                                                          |
| System files      | `/proc/stat`, `/proc/meminfo`, `/proc/mounts`, `df -h` output        |

A new plugin file is added:

```python:src/sonic-utilities/dump/plugins/system_resource_monitor.py
"""
Techsupport plugin for system-resource-monitord.
"""

from dump.match_infra import MatchEngine, MatchRequest
from dump.helper import create_template_dict

TABLES = {
    "CONFIG_DB": [
        "SYSTEM_RESOURCE_MONITOR|*",
        "SYSTEM_RESOURCE_THRESHOLD|*"
    ],
    "STATE_DB": [
        "SYSTEM_CPU_UTILIZATION|*",
        "SYSTEM_CPU_UTILIZATION_HISTORY|*",
        "SYSTEM_MEMORY_UTILIZATION|*",
        "SYSTEM_MEMORY_UTILIZATION_HISTORY|*",
        "SYSTEM_STORAGE_DEVICE|*",
        "SYSTEM_STORAGE_PARTITION|*",
        "SYSTEM_RESOURCE_ALARM|*",
    ],
}

class SystemResourceMonitor:
    """Dump state for system resource monitoring."""

    def __init__(self, match_engine=None):
        self.match_engine = match_engine or MatchEngine()

    def collect(self, _):
        result = create_template_dict(dbs=list(TABLES.keys()))
        for db, patterns in TABLES.items():
            for pattern in patterns:
                req = MatchRequest(db=db, table="", key_pattern=pattern)
                ret = self.match_engine.fetch(req)
                result[db].update(ret.get("keys", {}))
        return result
```

#### 9.9.3 Health Check

The daemon registers itself with the SONiC `supervisord` watchdog pattern. A health check script verifies:

1. The `platformd ` process is running inside the pmon container.
2. STATE_DB `CPU_TABLE|0|0` has a `timestamp` within the last 60 seconds.
3. CONFIG_DB `CPU_GLOBAL|global` exists.

#!/bin/bash
# Health check for platformd

# Check process is running
if ! pgrep -f "platformd" > /dev/null 2>&1; then
    echo "FAIL: platformd process not running"
    exit 1
fi

# Check STATE_DB freshness (timestamp within last 60 seconds)
TIMESTAMP=$(redis-cli -n 6 HGET "CPU_TABLE|0|0" "timestamp" 2>/dev/null)
if [ -z "$TIMESTAMP" ]; then
    echo "FAIL: No CPU utilization data in STATE_DB"
    exit 1
fi

EPOCH_NOW=$(date +%s)
EPOCH_TS=$(date -d "$TIMESTAMP" +%s 2>/dev/null)
if [ $? -ne 0 ] || [ $((EPOCH_NOW - EPOCH_TS)) -gt 60 ]; then
    echo "FAIL: CPU utilization data is stale"
    exit 1
fi

echo "PASS: platformd is healthy"
exit 0
```
---

### 10. Warmboot and Fastboot Design Impact

#### 10.1 Warm Boot Requirements

- Configuration (thresholds, intervals, fan settings, temperature unit) shall be retained across warm boot.
- History data in STATE_DB will be lost on any restart (by design).
- Threshold alarms shall be re-evaluated after restart; no stale alarms shall persist.

#### 10.2 Warm Boot Support

| Aspect | Behavior |
|--------|----------|
| **Configuration persistence** | All CONFIG_DB tables (`SYSTEM_RESOURCE_MONITOR`, `SYSTEM_RESOURCE_THRESHOLD`, `FAN_CONFIG`) are persisted to `config_db.json` and survive warm, fast, and cold reboots. |
| **History data** | Stored in STATE_DB and is **not preserved** across any reboot type. This is by design per requirements FR-2 and FR-4. On daemon restart, history buffers are re-initialized empty. |
| **Threshold alarms** | On restart, all `SYSTEM_RESOURCE_ALARM` entries in STATE_DB are cleared. The daemon re-evaluates thresholds on the first collection cycle and raises new alarms as needed. There is no stale-alarm carry-over. |
| **During warm boot** | The daemon is stopped before warm boot and restarted after. Since this feature operates purely in the management/platform plane, there is **no impact on dataplane traffic** during warm boot. |

---
### 11. Memory Consumption

### 12. Restrictions/Limitations

1. **History Data Persistence**
   - History data is stored in STATE_DB (volatile memory)
   - History is lost on system restart, warmboot, or fastboot
   - No persistent storage of historical metrics

2. **CPU Monitoring Scope**
   - Only per-logical-core CPU utilization is supported
   - Per-container CPU utilization is not supported
   - Aggregate CPU utilization across all cores is not provided
   - Per-socket CPU utilization for multi-socket systems is not supported

3. **Storage Monitoring Scope**
   - Only permanently attached storage devices are monitored
   - Removable storage (USB drives) is excluded
   - Only mounted partitions are reported
   - Aggregate device-level utilization is not provided

4. **Threshold Monitoring**
   - Only maximum thresholds are supported (CPU, memory, disk)
   - Minimum thresholds are not supported
   - Per-core CPU thresholds are not supported (only aggregate)
   - Per-partition disk thresholds are not supported

5. **Alarm Notification**
   - Syslog is the only mandatory notification mechanism
   - SNMP traps and other notification methods are out of scope
   - No alarm rate limiting or suppression

6. **History Configuration**
   - History interval must be less than history duration
   - Maximum history duration is 1440 minutes (24 hours)
   - Maximum history interval is 60 minutes
   - Changing history configuration clears existing history data

7. **Performance Considerations**
   - Metric collection uses system resources (CPU, I/O)
   - Very short history intervals may impact system performance
   - Recommended minimum history interval is 5 minutes

### 13. Testing Requirements/Design

#### 13.1 Unit Test Cases

Unit tests are implemented using `pytest` with mocked file I/O and Redis connections.

| Test ID | Test Case                                                                       | Expected Result                        |
|---------|---------------------------------------------------------------------------------|----------------------------------------|
| UT-01   | Parse `/proc/stat` with 4 cores                                                 | Returns dict with 4 `CpuTimes` entries |
| UT-02   | Parse `/proc/stat` with 128 cores                                               | Returns dict with 128 entries          |
| UT-03   | CPU utilization calculation: idle_delta=20, total_delta=100                     | Returns 80.0%                          |
| UT-04   | CPU utilization calculation: total_delta=0 (edge case)                          | Returns 0.0% (no division by zero)     |
| UT-05   | Parse `/proc/meminfo` standard format                                           | Returns correct total, available, used, usage_percent |
| UT-06   | Memory usage percent calculation: used=8192MB, total=16384MB                    | Returns 50.0%                          |
| UT-07   | Circular buffer: add 5 entries to buffer of size 12                             | `get_all()` returns 5 entries in order |
| UT-08   | Circular buffer: add 15 entries to buffer of size 12                            | `get_all()` returns last 12 entries in order |
| UT-09   | Circular buffer: add exactly 12 entries to buffer of size 12                    | `get_all()` returns all 12 in order    |
| UT-10   | Storage partition discovery: mock `/proc/mounts` with 3 permanent + 1 removable | Returns only 3 permanent partitions    |
| UT-11   | Storage partition: removable device (`/sys/block/sdb/removable == 1`)           | Excluded from results                  |
| UT-12   | Storage partition: `tmpfs`, `devtmpfs`, `proc`                                  | Excluded from results                  |
| UT-13   | Storage utilization: used=750MB, total=1000MB                                   | Returns 75.0%                          |
| UT-14   | Threshold alarm: CPU at 90%, threshold 85% (previously cleared)                 | Alarm raised, status=active            |
| UT-15   | Threshold alarm: CPU at 80%, threshold 85% (previously active)                  | Alarm cleared, status=cleared          |
| UT-16   | Threshold alarm: CPU at 90%, threshold 85% (already active)                     | No state change (no duplicate alarm)   |
| UT-17   | Threshold alarm: CPU at 80%, threshold 85% (already cleared)                    | No state change |
| UT-18   | Disk threshold: 3 partitions, 1 exceeds threshold                               | Alarm raised only for the exceeding partition |
| UT-19   | Disk threshold: partition unmounted between cycles                              | Alarm for that partition auto-cleared, STATE_DB entry removed |
| UT-20   | CONFIG_DB change: interval 5→10 minutes                                         | History buffer re-initialized, max_entries recalculated |
| UT-21   | CONFIG_DB change: invalid interval > duration                                   | Change rejected by YANG validation     |
| UT-22   | CONFIG_DB missing at startup                                                    | Daemon uses defaults (duration=60, interval=5, thresholds=85/80/75) |
| UT-23   | Syslog message format: alarm raised                                             | Contains `ALARM RAISED`, alarm ID, current value, threshold |
| UT-24   | Syslog message format: alarm cleared                                            | Contains `ALARM CLEARED`, alarm ID, current value, threshold |
| UT-34   | STATE_DB cleanup on daemon restart                                              | All `*_HISTORY` and `SYSTEM_RESOURCE_ALARM` keys cleared |
| UT-35   | YANG validation: cpu_history_duration=60, interval=7                            | Rejected (60 not divisible by 7)       |
| UT-36   | YANG validation: max_threshold=0                                                | Rejected (range 1-100)                 |
| UT-37   | YANG validation: max_threshold=101                                              | Rejected (range 1-100)                 |
| UT-38   | YANG validation: temperature_unit="kelvin"                                      | Rejected (not in enum)                 |

#### 13.2 Functional Tests

End-to-end functional tests using `pytest` with a running SONiC instance or VS (Virtual Switch) environment.

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| FT-01 | CPU snapshot retrieval | 1. Wait for daemon to run one cycle. 2. `show system-resource cpu` | Displays per-core utilization with valid percentages (0-100) and recent timestamp |
| FT-02 | CPU history with default config | 1. Use default config (60 min, 5 min interval). 2. Wait 5+ minutes. 3. `show system-resource cpu history` | At least 1 history entry per core |
| FT-03 | CPU history with custom config | 1. `config system-resource history cpu interval 2`. 2. `config system-resource history cpu duration 10`. 3. Wait 4+ minutes. 4. `show system-resource cpu history` | At least 2 history entries; max 5 entries (10/2) |
| FT-04 | Memory snapshot retrieval | 1. `show system-resource memory` | Shows total, used, available in MB and usage percentage |
| FT-05 | Memory history with default config | 1. Wait 5+ minutes. 2. `show system-resource memory history` | At least 1 history entry |
| FT-06 | Storage partition listing | 1. `show system-resource storage` | Lists devices with partition counts and mounted partition utilization |
| FT-07 | Storage excludes removable devices | 1. Insert USB (if applicable). 2. `show system-resource storage` | USB partitions not listed |
| FT-08 | CPU threshold alarm — raise | 1. `config system-resource threshold cpu 10` (low threshold to trigger). 2. Wait one cycle. 3. `show system-resource alarms` | `CPU_UTILIZATION_HIGH` alarm is active |
| FT-09 | CPU threshold alarm — clear | 1. `config system-resource threshold cpu 99` (high threshold to clear). 2. Wait one cycle. 3. `show system-resource alarms` | `CPU_UTILIZATION_HIGH` alarm is cleared |
| FT-10 | Memory threshold alarm | 1. Set threshold below current usage. 2. Verify alarm raised. 3. Set threshold above current usage. 4. Verify alarm cleared | Alarm lifecycle works correctly |
| FT-11 | Disk threshold alarm — per partition | 1. Set disk threshold to 5%. 2. Wait one cycle. 3. `show system-resource alarms` | Individual alarms for each partition exceeding 5% |
| FT-12 | Syslog verification — alarm raised | 1. Trigger CPU alarm (set threshold low). 2. Check `journalctl -u system-resource-monitord` | Syslog contains `ALARM RAISED — CPU_UTILIZATION_HIGH` at WARNING level |
| FT-13 | Syslog verification — alarm cleared | 1. Clear CPU alarm (set threshold high). 2. Check syslog | Syslog contains `ALARM CLEARED — CPU_UTILIZATION_HIGH` at NOTICE level |
| FT-14 | Default threshold values | 1. Remove all threshold config. 2. Restart daemon. 3. `show system-resource threshold` | CPU=85%, MEMORY=80%, DISK=75% |
| FT-15 | History not persisted across reboot | 1. Verify history has entries. 2. Reboot. 3. `show system-resource cpu history` | History is empty after reboot |
| FT-16 | Config persisted across reboot | 1. `config system-resource threshold cpu 90`. 2. Reboot. 3. `show system-resource config` | CPU threshold is still 90% |
| FT-17 | Show config command | 1. Configure various parameters. 2. `show system-resource config` | All configured values displayed correctly |
| FT-18 | REST API — GET CPU utilization | 1. `curl GET /restconf/data/.../SYSTEM_CPU_UTILIZATION` | JSON response with per-core utilization |
| FT-19 | REST API — PATCH threshold | 1. `curl PATCH` CPU threshold to 92. 2. `curl GET` thresholds | CPU threshold updated to 92 |
| FT-20 | gNMI — subscribe to CPU utilization | 1. gNMI subscribe (STREAM). 2. Wait for updates | Receives periodic CPU utilization updates |
| FT-21 | Clear history command | 1. Verify history exists. 2. `sonic-clear system-resource history cpu`. 3. `show system-resource cpu history` | History is empty |
| FT-22 | Clear alarms command | 1. Trigger alarm. 2. `sonic-clear system-resource alarms`. 3. `show system-resource alarms` | No active alarms (re-evaluated on next cycle) |
| FT-23 | Multiple cores — max utilization alarm | 1. Set CPU threshold to 50%. 2. Stress one core. 3. Verify alarm raised | Alarm raised referencing the highest-utilization core |
| FT-24 | Daemon restart recovery | 1. `systemctl restart system-resource-monitord`. 2. Wait 15 seconds. 3. `show system-resource cpu` | Data collection resumes; current snapshot available |

#### 13.3. System Test cases

1. CPU Utilization Monitoring

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-CPU-001 | Current CPU Utilization Per Core 1. Query current CPU utilization for all cores 2. Verify data returned for each logical CPU core 3. Validate utilization values are within 0-100% range 4. Compare with Linux tools (top, mpstat) for accuracy    |CPU utilization reported for each logical core- Values accurate within ±5% of Linux tool readings Data format consistent and parseable
| TC-CPU-002 | CPU Utilization History with Default Settings | 1. Verify default history duration is 60 minutes 2. Verify default measure 5 minutes 3 multiple measurement intervals 4. Query CPU utilization history 5. Verify history contains data points at 5-minute intervals | History duration: 60 minutes- Measurement interval: 5 minutes History contains up to 12 data points (60/5)  Each value represents average CPU usage during interval
| TC-CPU-003 | CPU Utilization History with Custom Settings | 1. Configure custom history duration (e.g., 30 minutes) 2. Configure custom measurement interval (e.g., 2 minutes) 3. Wait for multiple intervals 4. Query CPU utilization history 5. Verify history reflects custom settings | History duration matches configured value Measurement interval matches configured value  Data points collected at configured intervals
| TC-CPU-004 | CPU History Data After Reboot | 1. Collect CPU utilization history 2. Verify history contains data 3. Reboot system 4. Query CPU utilization history after reboot| History cleared after reboot New history collection starts from zero
| TC-CPU-005 | CPU Utilization Under Load |    1. Query baseline CPU utilization 2. Generate 50% CPU load using stress tool 3. Query CPU utilization, verify ~50% usage 4. Generate 100% CPU load 5. Query CPU utilization, verify ~100% usage 6. Stop load, verify utilization returns to baseline | CPU utilization accurately reflects load conditions  Per-core utilization reported correctly History captures load variations

2. Memory Utilization Monitoring

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-MEM-001 |    Current Memory Utilization Snapshot | 1. Query current memory utilization 2. Verify available and used memory reported 3. Compare with Linux tools (free, vmstat) 4. Validate total = available + used | Available and used memory reported Values accurate within ±2% of Linux tools| Units clearly specified (MB, GB, or percentage)
| TC-MEM-002 | Memory Utilization History with Default Settings | 1. Verify default history duration is 60 minutes 2. Verify default measurement interval is 5 minutes 3. Wait for multiple measurement intervals 4. Query memory utilization history 5. Verify history data points    | History duration: 60 minutes Measurement interval: 5 minutes  Up to 12 historical data points available  Each value represents average during interval
| TC-MEM-003 |    Memory Utilization History with Custom Settings | 1. Configure custom history duration (e.g., 45 minutes) 2. Configure custom measurement interval (e.g., 3 minutes) 3. Wait for data collection 4. Query memory history 5. Verify custom settings applied    | History reflects configured duration Measurement interval matches configuration  Data collected at specified intervals
| TC-MEM-004 |    Memory History Non-Persistence | 1. Collect memory utilization history 2. Reboot system 3. Query memory history after reboot    | History cleared after reboot  Fresh history collection begins
| TC-MEM-005 |    Memory Utilization Under Load |    1. Query baseline memory utilization 2. Allocate memory to increase usage to 50% 3. Query memory utilization, verify increase 4. Allocate more memory to reach 80% 5. Query utilization, verify high usage 6. Release memory, verify utilization decreases | Memory utilization accurately reflects allocation| History captures memory usage changes

3. Storage Monitoring 

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-STG-001 |    Storage Partition Information |    1. Query storage partition information 2. Verify number of partitions reported 3. Compare with Linux df command 4. Verify only mounted partitions included    | All mounted partitions reported  Partition count accurate  Only permanently attached storage included  Removable devices excluded
| TC-STG-002 |    Storage Partition Utilization | 1. Query partition utilization for all partitions 2. Verify utilization percentage for each partition 3. Compare with df -h output 4. Validate utilization values (0-100%)    | Utilization percentage reported for each partition  Values match df command (±1%)  Only mounted partitions show utilization
| TC-STG-003 |    Storage Utilization Changes    | 1. Query initial storage utilization 2. Create large files to increase usage by 10% 3. Query utilization, verify increase 4. Delete files 5. Query utilization, verify decrease | Utilization accurately reflects storage changes  Updates visible in real-time queries


4. Memory Threshold and Alarming

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-MEMT-001 |    Memory Threshold Default Value | 1. Query memory utilization threshold 2. Verify default threshold is 80% | Default memory threshold: 80%
| TC-MEMT-002 |    Memory Threshold Configuration | 1. Configure memory threshold to 70% 2. Verify configuration accepted 3. Query threshold, verify value 4. Configure to different value (85%) 5. Verify new configuration | Threshold configuration successful Values persist correctly Valid range: 1-100%
| TC-MEMT-003 |    Memory Threshold Alarm Generation |    1. Configure memory threshold to 60% 2. Clear syslog 3. Allocate memory to exceed 60% utilization 4. Wait for alarm generation 5. Check syslog for alarm message | Alarm generated when memory exceeds threshold Syslog contains alarm with details Message includes threshold and current utilization
| TC-MEMT-004 |    Memory Threshold Alarm Clearing    | 1. Trigger memory threshold alarm 2. Verify alarm active 3. Release memory to drop below threshold 4. Wait for alarm clearing 5. Check syslog for clear message | Alarm clears automatically Syslog contains clear message Alarm state updated correctly

5. Storage Threshold Configuration

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-STGT-001 | Storage Threshold Default Value | 1. Query storage utilization threshold 2. Verify default threshold is 75% |     Default storage threshold: 75%
| TC-STGT-002 | Storage Threshold Configuration | 1. Configure storage threshold to 65% 2. Verify configuration accepted 3. Query threshold value 4. Reconfigure to 80% 5. Verify new value    Threshold configuration successful | Values persist Valid range: 1-100%
| TC-STGT-003 |    Storage Threshold Alarm Generation | 1. Configure storage threshold to 60% 2. Clear syslog 3. Create files to exceed 60% utilization 4. Wait for alarm generation 5. Check syslog for alarm    Alarm generated when storage exceeds threshold |  Syslog contains alarm message Message includes partition and utilization
| TC-STGT-004 |    Storage Threshold Alarm Clearing |    1. Trigger storage threshold alarm 2. Verify alarm active 3. Delete files to drop below threshold 4. Wait for alarm clearing 5. Check syslog for clear message    | Alarm clears automatically Syslog contains clear message Alarm state transitions correctly
| TC-STGT-005 |    Storage Threshold Per Partition    | 1. Configure storage threshold 2. Fill one partition above threshold 3. Verify alarm for that partition only 4. Fill second partition above threshold 5. Verify separate alarm for second partition 6. Clear first partition 7. Verify only first alarm clears | Alarms generated per partition independently Each partition monitored separately Alarm messages identify specific partition

6. Syslog Format

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-SYSLOG-001 |     Syslog Format - CPU Alarm |    1. Trigger CPU threshold alarm 2. Capture syslog message 3. Verify message contains: Timestamp, Resource type (CPU), Threshold value, Current utilization, Alarm state (active/cleared)    | Syslog message well-formatted All required information present Message parseable for automation
| TC-SYSLOG-002 | Syslog Format - Memory Alarm    | 1. Trigger memory threshold alarm 2. Capture syslog message 3. Verify message format and content    | Syslog message contains resource type, threshold, utilization Format consistent with CPU alarm messages
| TC-SYSLOG-003 |    Syslog Format - Storage Alarm | 1. Trigger storage threshold alarm 2. Capture syslog message 3. Verify message includes partition information | Syslog message identifies specific partition Contains threshold and utilization data Format consistent with other alarms
| TC-SYSLOG-004 | Syslog Alarm and Clear Messages |    1. Trigger CPU threshold alarm 2. Capture alarm message 3. Clear alarm condition 4. Capture clear message 5. Compare message formats |    Both alarm and clear messages logged Messages clearly distinguish alarm vs. clear state Correlation possible between alarm and clear

7. Multiple Resource Monitoring

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-CONC-001 |    Multiple Resource Monitoring | 1. Query CPU, memory, storage, temperature, and fan data simultaneously 2. Verify all queries return successfully 3. Validate data accuracy for each resource 4. Repeat queries multiple times | All resources monitored concurrently No interference between monitoring functions Data accuracy maintained
| TC-CONC-002 |    Multiple Threshold Violations |    1. Configure thresholds for CPU, memory, and storage 2. Trigger all three thresholds simultaneously 3. Verify all alarms generated 4. Check syslog for all alarm messages 5. Clear all conditions 6. Verify all alarms clear | All threshold violations detected Separate alarms for each resource All alarms logged to syslog Independent alarm clearing

8. Threshold Configuration

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-CONF-001 | Threshold Configuration Persistence |    1. Configure custom thresholds for CPU, memory, storage 2. Save configuration 3. Reboot system 4. Query threshold configurations 5. Verify values match pre-reboot settings | Threshold configurations persist Values restored correctly after reboot
| TC-CONF-002 | History Configuration Persistence | 1. Configure custom history duration and interval 2. Save configuration 3. Reboot system 4. Query history settings 5. Verify settings restored | History configuration persists Settings applied after reboot History data collection resumes with configured parameters


9. Configuration Persistence

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-CONF-001 |    Threshold Configuration Persistence | 1. Configure custom thresholds for CPU, memory, storage 2. Save configuration 3. Reboot system 4. Query threshold configurations 5. Verify values match pre-reboot settings | Threshold configurations persist Values restored correctly after reboot
| TC-CONF-002 | History Configuration Persistence |    1. Configure custom history duration and interval 2. Save configuration 3. Reboot system 4. Query history settings 5. Verify settings restored | History configuration persists Settings applied after reboot History data collection resumes with configured parameters


10. Invalid values

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-NEG-001 | Invalid Threshold Values | 1. Attempt to configure CPU threshold to 0% 2. Attempt to configure memory threshold to 101% 3. Attempt to configure storage threshold to -10% 4. Attempt to configure threshold with non-numeric value 5. Verify all invalid configurations rejected | Invalid values rejected with error messages Current threshold values unchanged System remains stable
| TC-NEG-002 | Invalid History Configuration | 1. Attempt to configure negative history duration 2. Attempt to configure zero measurement interval 3. Attempt to configure excessively large values 4. Verify rejections | Invalid configurations rejected Appropriate error messages Default or current values retained
| TC-NEG-003 | Resource Monitoring Under Stress    1. Generate maximum CPU load (100% all cores) 2. Allocate maximum available memory 3. Fill storage to near capacity 4. Query all monitoring data 5. Verify monitoring functions remain operational    |Monitoring continues under stress Data remains accurate No system crashes or hangs

11. Query Response

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-PERF-001 |    Monitoring Query Response Time | 1. Query CPU utilization, measure response time 2. Query memory utilization, measure response time 3. Query storage information, measure response time 4. Query temperature, measure response time 5. Query fan information, measure response time 6. Verify all queries complete within 2 seconds |    All queries respond within 2 seconds Response time consistent across queries
| TC-PERF-002 | History Data Retrieval Performance | 1. Collect full 60 minutes of history data 2. Query complete CPU history, measure time 3. Query complete memory history, measure time 4. Verify retrieval time acceptable (< 5 seconds) | History retrieval completes within 5 seconds Large datasets handled efficiently
| TC-PERF-003 | Monitoring Overhead    | 1. Measure baseline CPU usage without monitoring 2. Enable all monitoring features 3. Measure CPU usage with monitoring active 4. Calculate monitoring overhead 5. Verify overhead < 5% CPU | Monitoring overhead minimal (< 5% CPU) No significant memory consumption No impact on system performance

12. Cleared configuration

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-HIST-001 | Oldest Entry Removal When Buffer Full | 1. Configure history duration to 60 minutes with 5-minute intervals (12 entries max) 2. Wait for buffer to fill completely (60+ minutes) 3. Verify buffer contains exactly 12 entries 4. Wait for one more interval (5 minutes) 5. Query history and verify: Buffer still contains 12 entries, Oldest entry removed, Newest entry added 6. Record timestamps of first and last entries 7. Wait for another interval 8. Verify timestamps shifted (FIFO behavior) | Buffer maintains maximum size (duration/interval entries) Oldest entries automatically removed when buffer full FIFO (First-In-First-Out) behavior confirmed No buffer overflow or data corruption
| TC-HIST-002 | History Cleared on Configuration Change | 1. Configure history duration to 60 minutes, interval 5 minutes 2. Wait for history data to accumulate (at least 6 entries) 3. Verify history contains data 4. Change history duration to 30 minutes 5. Query history immediately 6. Verify history is cleared/empty 7. Wait for new data collection 8. Verify new history follows new configuration | History cleared when duration changes History cleared when interval changes New history collection starts with new parameters No stale data from previous configuration
| TC-HIST-003 | History Data Format Validation | 1. Configure history collection for CPU and memory 2. Wait for multiple data points to collect 3. Query CPU utilization history 4. Verify response is valid JSON 5. Verify structure is JSON array 6. Validate each array element contains: Timestamp, Utilization value(s), Per-core data (for CPU) 7. Query memory utilization history 8. Verify same JSON array format 9. Parse JSON programmatically to confirm validity | History data returned as valid JSON array Array elements properly formatted Timestamps in ISO 8601 or Unix epoch format Data parseable by standard JSON libraries Schema consistent across resource types
| TC-HIST-004 | History Lost on Daemon Restart | 1. Start SRM daemon 2. Configure history collection 3. Wait for history data to accumulate (at least 30 minutes) 4. Query and record history data (verify multiple entries exist) 5. Restart SRM daemon (systemctl restart srm) 6. Wait for daemon to fully restart 7. Query history data 8. Verify history is empty/cleared 9. Wait for new data collection 10. Verify new history starts from zero | History data cleared on daemon restart No persistence of history to disk New history collection begins after restart Configuration settings preserved (duration/interval) Only history data is lost, not configuration

13. Alarm Test

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-ALARM-001 | Alarm Message Content Validation | 1. Configure CPU threshold to 60% 2. Clear syslog 3. Trigger CPU threshold violation 4. Capture alarm message from syslog 5. Verify message contains: Timestamp (accurate to second), Severity level (WARNING or CRITICAL), Resource type (CPU/Memory/Storage), Resource identifier (core number, partition name), Threshold value configured, Current utilization value, Alarm state (ACTIVE/RAISED), Unique alarm identifier (optional) 6. Repeat for memory and storage alarms 7. Verify consistent format across all alarm types | All required fields present in alarm message Timestamp accurate Values correct (threshold and current) Message format consistent and parseable Severity level appropriate for violation magnitude
| TC-ALARM-002 | No Duplicate Alarms for Same Condition | 1. Configure CPU threshold to 60% 2. Clear syslog 3. Generate CPU load to exceed 60% (e.g., 75%) 4. Wait for initial alarm generation 5. Verify alarm message in syslog 6. Maintain CPU load above threshold for 30 minutes 7. Monitor syslog continuously 8. Count alarm messages for same condition 9. Verify only ONE alarm message generated 10. Reduce load below threshold 11. Wait for clear message 12. Trigger threshold again 13. Verify new alarm generated (this is expected)    | Only one alarm message per threshold violation No duplicate/repeated alarms while condition persists Alarm remains "active" until condition clears New alarm generated only after clear and re-trigger Syslog not flooded with duplicate messages
| TC-ALARM-003 | Alarm Hysteresis - No Flapping | 1. Configure CPU threshold to 70% 2. Clear syslog 3. Generate load to reach exactly 70% (at threshold) 4. Vary load to oscillate between 69-71% rapidly 5. Maintain oscillation for 10 minutes 6. Monitor syslog for alarm messages 7. Count alarm and clear messages 8. Verify hysteresis mechanism prevents flapping | Hysteresis prevents alarm flapping Alarm requires sustained violation to trigger (e.g., 2-3 consecutive measurements) Clear requires sustained recovery (e.g., 2-3 consecutive measurements below threshold) No rapid alarm/clear/alarm/clear sequences

14. Warm Boot
| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-WB-001 | Warm Boot with SRM Running | 1. Verify SRM daemon is running (systemctl status srm) 2. Configure SRM with custom settings: CPU threshold 70%, Memory threshold 75%, History duration 45 minutes, History interval 3 minutes 3. Collect some history data (wait 15 minutes) 4. Enable warm boot mode 5. Initiate warm boot (warm-reboot command) 6. Monitor system during warm boot 7. After boot completion, verify: System boots successfully, SRM daemon restarts automatically, No kernel panic or system errors 8. Check SRM daemon status 9. Verify basic monitoring functions operational | System completes warm boot successfully SRM daemon restarts automatically No data plane disruption (warm boot characteristic) SRM operational after boot Boot time within expected warm boot duration
| TC-WB-002 | Configuration Preserved After Warm Boot | 1. Configure SRM with specific settings: CPU threshold 65%, Memory threshold 78%, Storage threshold 72%, History duration 30 minutes, History interval 2 minutes, Temperature unit Fahrenheit 2. Save configuration 3. Verify configuration active 4. Perform warm boot 5. After boot, query all configuration parameters 6. Verify all settings match pre-boot values: All thresholds preserved, History parameters preserved, Temperature unit preserved 7. Verify configuration file integrity | All configuration parameters preserved Thresholds remain as configured History settings retained Temperature unit setting preserved No configuration loss or corruption
| TC-WB-003 | History Cleared After Warm Boot | 1. Configure history collection (60 min duration, 5 min interval) 2. Wait for substantial history data (at least 30 minutes) 3. Query and record history data (verify multiple entries) 4. Perform warm boot 5. After boot completion, query CPU history 6. Verify history is empty 7. Query memory history 8. Verify history is empty 9. Wait for new data collection 10. Verify new history starts from zero | All history data cleared after warm boot CPU history empty after boot Memory history empty after boot Configuration preserved (duration/interval) New history collection begins post-boot No stale pre-boot data in history
| TC-WB-004 | Metric Collection Resumes After Warm Boot | 1. Configure SRM with history collection 2. Perform warm boot 3. After boot, immediately verify: Current CPU utilization queryable, Current memory utilization queryable, Current storage utilization queryable, Temperature readings available, Fan status available 4. Wait for one history interval (e.g., 5 minutes) 5. Query history 6. Verify new data point collected 7. Wait for multiple intervals 8. Verify continuous data collection 9. Generate threshold violation 10. Verify alarm generation works | Current metrics available immediately after boot History collection resumes automatically Data collected at configured intervals All monitoring functions operational Alarm generation functional No manual intervention required
| TC-WB-005 | Fast Boot with SRM Running | 1. Configure SRM with custom settings 2. Collect history data 3. Initiate fast boot (fast-reboot command) 4. Monitor boot process 5. After boot, verify: System boots successfully, SRM daemon restarts, Configuration preserved, History cleared 6. Verify metric collection resumes 7. Compare boot time with warm boot | System completes fast boot successfully SRM daemon restarts automatically Configuration preserved (same as warm boot) History cleared (same as warm boot) Metric collection resumes Fast boot typically faster than warm boot All SRM functions operational post-boot

15. Stress Test

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-STRESS-001 | 24-Hour Continuous Operation | 1. Configure SRM with standard settings 2. Start SRM daemon 3. Run for 24 hours continuously 4. During 24-hour period, monitor: CPU usage of SRM daemon, Memory usage of SRM daemon, Daemon process status (no crashes), Log file size growth, History data collection continuity 5. Every 4 hours, perform: Query all current metrics, Query history data, Trigger and clear threshold alarms, Verify all functions operational 6. After 24 hours, verify: Daemon still running, No memory leaks (memory usage stable), No excessive CPU usage, All functions still operational, Log files manageable size | SRM runs continuously for 24+ hours No daemon crashes or restarts Memory usage stable (no leaks) CPU usage remains low (<5%) All monitoring functions remain accurate History collection continuous Alarm generation functional throughout Log rotation working (if configured)
| TC-STRESS-002 | Minimum History Interval Stress Test | 1. Configure history interval to minimum (1 minute) 2. Configure history duration to 60 minutes (60 entries) 3. Start monitoring 4. Run for 2 hours 5. Monitor system impact: SRM daemon CPU usage, SRM daemon memory usage, Disk I/O (if history persisted), System responsiveness 6. Verify data collection: Query history every 10 minutes, Verify data points collected every minute, Verify buffer management (oldest entries removed) 7. Verify accuracy: Compare with Linux tools, Verify no data loss, Verify timestamps accurate | SRM handles 1-minute interval without issues CPU overhead acceptable (<10%) Memory usage stable All data points collected accurately Buffer management works correctly (FIFO) No performance degradation System remains responsive
| TC-STRESS-003 | Maximum History Duration Stress Test | 1. Configure history duration to maximum (1440 minutes) 2. Configure history interval to 5 minutes (288 entries) 3. Run for 25+ hours to fill buffer 4. Monitor: Memory usage of SRM daemon, History query response time, Buffer management 5. Verify: All 288 entries stored correctly, Oldest entries removed when buffer full, Query performance acceptable (<5 seconds), Memory usage reasonable 6. Query complete history multiple times 7. Verify data integrity    SRM handles maximum duration configuration | Memory usage scales appropriately Query performance acceptable even with large dataset Buffer management works correctly No data corruption FIFO behavior maintained
| TC-STRESS-004 | Rapid Configuration Changes | 1. Create script to rapidly change configuration 2. Script performs 100 iterations of: Change CPU threshold (random 50-90%), Change memory threshold (random 50-90%), Change storage threshold (random 50-90%), Change history duration (random 30-120 min), Change history interval (random 1-10 min), Change temperature unit (Celsius/Fahrenheit), Wait 1 second between changes 3. Run script 4. Monitor: SRM daemon status (no crashes), Configuration file integrity, System logs for errors 5. After 100 changes, verify: Daemon still running, Final configuration applied correctly, No configuration corruption, Monitoring functions operational 6. Query all metrics 7. Trigger alarms to verify functionality | SRM handles rapid configuration changes No daemon crashes Configuration file remains valid Final configuration applied correctly No race conditions or deadlocks Monitoring functions remain operational History cleared appropriately on config changes No memory leaks from repeated reconfigurations

16. Other Sonic Services

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
| TC-INTEG-001 | SRM with Other SONiC Services | 1. Start all standard SONiC services (BGP, SWSS, syncd, etc.) 2. Start SRM daemon 3. Generate network traffic 4. Trigger SRM alarms 5. Verify: No interference with routing protocols, No impact on switching performance, SRM monitoring accurate during traffic 6. Restart individual services 7. Verify SRM continues operating    | SRM coexists peacefully with other services No resource contention Monitoring remains accurate No impact on network functions
| TC-INTEG-002 | SRM During System Upgrades | 1. Configure SRM 2. Collect history data 3. Perform SONiC image upgrade 4. After upgrade, verify: SRM configuration preserved, SRM daemon starts automatically, Monitoring functions operational 5. Verify compatibility with new SONiC version | Configuration survives upgrade SRM operational after upgrade No compatibility issues

17. SRM During System Upgrades

| Test ID | Test Case | Steps | Expected Result |
|---------|-----------|-------|-----------------|
|TC-UPGRADE-001 | Verify SRM behavior during SONiC upgrades |  1. Configure SRM 2. Collect history data 3. Perform SONiC image upgrade 4. After upgrade, verify: - SRM configuration preserved - SRM daemon starts automatically - Monitoring functions operational 5. Verify compatibility with new SONiC version | Configuration survives upgrade - SRM operational after upgrade - No compatibility issues

---

### 14. Open/Action items - if any 

## Appendix A: Default Configuration Summary

| Parameter | Default Value |
|-----------|--------------|
| CPU History Duration | 60 minutes |
| CPU History Interval | 5 minutes |
| Memory History Duration | 60 minutes |
| Memory History Interval | 5 minutes |
| CPU Max Threshold | 85% |
| Memory Max Threshold | 80% |
| Disk Max Threshold | 75% |

## Appendix B: init_cfg.json Defaults

These defaults are loaded via `init_cfg.json` during first boot or when no configuration exists:

```json:files/image_config/init_cfg/init_cfg.json.fragment
{
    "SYSTEM_RESOURCE_MONITOR": {
        "global": {
            "cpu_history_duration": "60",
            "cpu_history_interval": "5",
            "memory_history_duration": "60",
            "memory_history_interval": "5",
        }
    },
    "SYSTEM_RESOURCE_THRESHOLD": {
        "CPU": {
            "max_threshold": "85"
        },
        "MEMORY": {
            "max_threshold": "80"
        },
        "DISK": {
            "max_threshold": "75"
        }
    }
}
```

## Appendix C: Syslog Message Reference

| Event | Severity | Message Format |
|-------|----------|---------------|
| CPU alarm raised | `LOG_WARNING` | `ALARM RAISED — CPU_UTILIZATION_HIGH: CPU utilization at <X>% exceeds threshold <Y>%` |
| CPU alarm cleared | `LOG_NOTICE` | `ALARM CLEARED — CPU_UTILIZATION_HIGH: CPU utilization at <X>% is below threshold <Y>%` |
| Memory alarm raised | `LOG_WARNING` | `ALARM RAISED — MEMORY_UTILIZATION_HIGH: Memory utilization at <X>% exceeds threshold <Y>%` |
| Memory alarm cleared | `LOG_NOTICE` | `ALARM CLEARED — MEMORY_UTILIZATION_HIGH: Memory utilization at <X>% is below threshold <Y>%` |
| Disk alarm raised | `LOG_WARNING` | `ALARM RAISED — DISK_UTILIZATION_HIGH: Partition <path> utilization at <X>% exceeds threshold <Y>%` |
| Disk alarm cleared | `LOG_NOTICE` | `ALARM CLEARED — DISK_UTILIZATION_HIGH: Partition <path> utilization at <X>% is below threshold <Y>%` |
| Config changed | `LOG_INFO` | `Configuration updated: <parameter> changed from <old> to <new>` |
| Daemon started | `LOG_INFO` | `system-resource-monitord started. Config: duration=<X>, interval=<Y>` |
| Daemon stopped | `LOG_INFO` | `system-resource-monitord shutting down.` |
| History buffer reset | `LOG_INFO` | `History buffer reset due to configuration change.` |
| Collection error | `LOG_ERR` | `Failed to read <source>: <error details>` |

## Appendix D: Requirements Traceability Matrix

| Requirement | Design Section | DB Tables | CLI Commands | Test Cases |
|-------------|---------------|-----------|-------------|------------|
| FR-1 (CPU current) | 2.2.1, 3.3.2 | STATE_DB: `SYSTEM_CPU_UTILIZATION` | `show system-resource cpu` | UT-01–04, FT-01 |
| FR-2 (CPU history) | 2.2.1, 3.3.2 | STATE_DB: `SYSTEM_CPU_UTILIZATION_HISTORY` | `show system-resource cpu history`, `config system-resource history cpu` | UT-07–09, FT-02–03, FT-21, FT-27 |
| FR-3 (Memory current) | 2.2.2, 3.3.2 | STATE_DB: `SYSTEM_MEMORY_UTILIZATION` | `show system-resource memory` | UT-05–06, FT-04 |
| FR-4 (Memory history) | 2.2.2, 3.3.2 | STATE_DB: `SYSTEM_MEMORY_UTILIZATION_HISTORY` | `show system-resource memory history`, `config system-resource history memory` | UT-07–09, FT-05, FT-21 |
| FR-5 (Storage) | 2.2.3, 3.3.2 | STATE_DB: `SYSTEM_STORAGE_DEVICE`, `SYSTEM_STORAGE_PARTITION` | `show system-resource storage` | UT-10–13, FT-06–07 |
| FR-6 (CPU threshold) | 2.2.6, 3.3.3 | CONFIG_DB: `SYSTEM_RESOURCE_THRESHOLD|CPU`, STATE_DB: `SYSTEM_RESOURCE_ALARM` | `config system-resource threshold cpu`, `show system-resource threshold/alarms` | UT-17–20, FT-14–15, FT-20 |
| FR-7 (Memory threshold) | 2.2.6, 3.3.3 | CONFIG_DB: `SYSTEM_RESOURCE_THRESHOLD|MEMORY`, STATE_DB: `SYSTEM_RESOURCE_ALARM` | `config system-resource threshold memory`, `show system-resource threshold/alarms` | UT-17–20, FT-16, FT-20 |
| FR-8 (Disk threshold) | 2.2.6, 3.3.3 | CONFIG_DB: `SYSTEM_RESOURCE_THRESHOLD|DISK`, STATE_DB: `SYSTEM_RESOURCE_ALARM` | `config system-resource threshold disk`, `show system-resource threshold/alarms` | UT-21–22, FT-17, FT-20 |
| FR-9 (Syslog) | 2.2.7, 3.3.3 | N/A (syslog output) | N/A (verify via `journalctl`) | UT-30–31, FT-18–19 |
