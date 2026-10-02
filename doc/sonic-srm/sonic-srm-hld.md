# System Resource Monitoring

## Table of Contents

- [1.Revision](#1-revision)
- [2.Scope](#2-scope)
    - [2.1 In Scope](#21-in-scope)
    - [2.2 Out of Scope](#22-out-of-scope)
- [3. Definitions/Abbreviations](#3-definitions-abbreviations)
- [4. Feature Overview](#4-feature-overview)
- [5. Requirements](#5-requirements)
    - [5.1 Functional Requirements](#51-functional-requirements)
    - [5.2 Functional Description](#52-functional-description)
      - [5.2.1 CPU Utilization Monitoring](#521-cpu-utilization-monitoring)
      - [5.2.2 Memory Utilization Monitoring](#522-memory-utilization-monitoring)
      - [5.2.3 Storage/Disk Utilization Monitoring](#523-storage-disk-utilization-monitoring)
      - [5.2.4 Threshold-Based Alarming](#526-threshold-based-alarming)
      - [5.2.5 Syslog Notifications](#525-syslog-notifications)
    - [5.3 Target Deployment Use Cases](#53-target-deployment-use-cases)
    - [5.4 Scalability Requirements](#54-scalability-requirements)
      - [5.4.1 Redis Memory Footprint Estimation](#541-config-dbRedis-memory-footprint-estimation)
      - [5.4.2 CPU/RAM/STORAGE Overhead](#542-cpu/ram/storage-overhead)
- [6. Architecture Design](#6-architecture-design)
    - [6.1 Basic Approach ](#61-basic-approach)
    - [6.2 Container ](#62-container)
- [7. High-Level Design](#7-high-level-design)
    - [7.1 Overview](#71-design-overview)
    - [7.2 DB Schema](#72-db-schema)
      - [7.2.1 CONFIG_DB](#721-config_db)
      - [7.2.2 STATE_DB](#722-state_db)
    - [7.3 Flow Diagrams](#73-flow-diagrams)
      - [7.3.1 Resource Collection Flow](#731-resource-collection-flow)
      - [7.3.2 Threshold Alarm Flow](#732-threshold-alarm-flow)
    - [7.4 Sequence Diagram](#74-sequence-diagrams)
- [8. Configuration and Management](#8-configuration-and-management)
    - [8.1 Daemon Design](#81-daemon-design)
      - [8.1.1 platformmond](#811-platformmond)
      - [8.1.2 stormond](#914-stormond)
    - [8.2 CLI](#82-cli)
      - [8.2.1 Configuration Commands](#821-configuration-commands)
      - [8.2.2 Show Commands](#822-show-commands)
	- [8.3 YANG Model](#83-yang-model)
    - [8.4 Error Handling](#84-error-handling)
	  - [8.4.1 Database Connection Errors](#841-database-connection-errors)
      - [8.4.2 Data Collection Errors](#842-data-collection-errors)
      - [8.4.3 Configuration Errors](#843-configuration-errors)
      - [8.4.4 Alarm Processing Errors](#844-alarm-processing-errors)
      - [8.4.5 Daemon Lifecycle Errors](#846-daemon-lifecycle-errors)
      - [8.4.6 Infrastructure Errors](#847-Infrastructure-errors)
      - [8.4.7 CLI Errors](#848-cli-errors)
    - [8.5 Error Recovery Summary](#85-error-recovery-summary)
    - [8.6 Serviceability and Debug](#86-serviceability-and-debug)
      - [8.6.1 Logging](#861-logging)
      - [8.6.2 Techsupport Integration](#862-techsupport-integration)
- [9. Warmboot and Fastboot Design Impact](#9-warmboot-and-fastboot-design-impact)
    - [9.1 Warm Boot Requirements](#91-warm-boot-requirements)
    - [9.2 Warm Boot Support](#92-warm-boot-support)
- [10. Restrictions/Limitations](#10-restrictionslimitations) 
- [11. Testing Requirements/Design](#11-testing-requirementsdesign)
    - [11.1 Unit Test Cases](#111-unit-test-cases)
    - [11.2 System Test Cases](#112-system-test-cases)
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
5. REST API Support
6. gNMI Support                                 
7. SNMP traps (may be added later)                        

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

### 4. Feature Overview

This document provides a high-level design for the System Resource Monitoring (SRM) feature in SONiC, enabling proactive system health management and prevent resource exhaustion. It covers CPU, memory, and storage utilization monitoring with history and threshold-based alarming; and syslog-based notifications. The document is written so that a new engineer or architect joining the SONiC community can understand the end-to-end feature design.

### 5 Requirements

#### 5.1 Functional Requirements

| ID    | Requirement Summary                                                                                                             |
|-------|-----------------------------------------------------------------------------------------------------------------------------    |
| FR-1  | Retrieve current snapshot of CPU utilization **per logical core**.                                                              |
| FR-2  | Retrieve CPU utilization **history per core** for a configurable duration (default 60 min) at a configurable measurement interval (default 5 min). Each value is the average utilization during that interval. History is read-only and non-persistent across restarts. |
| FR-3  | Retrieve current snapshot of system-level physical memory (RAM): Total, available and used.                                            |
| FR-4  | Retrieve memory utilization **history** for a configurable duration (default 60 min) at a configurable measurement interval (default 5 min). History is read-only and non-persistent across restarts.  |
| FR-5  | Retrieve storage partition information and utilization for all permanently attached storage devices. Report number of partitions per device and utilization percentage of each mounted partition. Removable devices excluded. |
| FR-6  | Support configurable maximum CPU utilization threshold (default 85 %). Generate alarm when exceeded; auto-clear when below.     |
| FR-7  | Support configurable maximum memory utilization threshold (default 80 %). Generate alarm when exceeded; auto-clear when below.  |
| FR-8  | Support configurable maximum flash/disk utilization threshold (default 75 %). Generate alarm when exceeded; auto-clear when below.|
| FR-9  | Generate syslog notifications for all threshold violations (raise and clear).                                               |

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
[s0] [s1] [s2] [s3] ... [s11] [s0'] ← oldest deleted, new inserted at the end

##### 5.2.2 Memory Utilization Monitoring

**Current Snapshot (FR-3):**

The daemon monitors system-level physical memory (RAM) by periodically reading and parsing `/proc/meminfo`. 
It computes memory availability, usage, and utilization percentage to provide real-time memory statistics.

**Data Source:** `/proc/meminfo`

**Relevant Fields:**

- **MemTotal** - Total physical RAM installed on the system (in kB, converted to bytes internally)
- **MemAvailable** - Estimate of memory available for starting new applications without swapping (in kB, converted to bytes internally)

*Note: MemAvailable is preferred over MemFree as it accounts for reclaimable memory (buffers, caches) and provides a more accurate representation of usable memory.*

**Computation Logic**

**Metrics Calculated:**

- **Total Physical RAM:**
total_memory = MemTotal × 1024 (from /proc/meminfo)


- **Available Memory:**
available_memory = MemAvailable × 1024 (from /proc/meminfo)


- **Used Memory:**
used_memory = total_memory − available_memory

- **Memory Utilization Percentage:**
memory_utilization = round((used_memory / total_memory) × 100)

**Polling Mechanism**

- **Polling Interval:** 5 seconds (System-wide)
- **Precision:** Bytes (Internally stored in bytes (converted from kB))

**Rationale for 5-Second Interval**

**System Overhead:** Minimal CPU impact; `/proc/meminfo` read is a lightweight operation

**Store in STATE_DB:** Update memory snapshot in STATE_DB

**Example Workflow**

- **T=0** - Daemon starts; initial read of `/proc/meminfo`
- Parses: MemTotal=16384000 kB, MemAvailable=8192000 kB
- Convert total_memory=16777216000 bytes, available_memory=8388608000 bytes
- Compute used_memory=8388608000 bytes, memory_utilization=50%
- Stores snapshot in STATE_DB

- **T=5** - Second poll triggered
- Reads updated values from `/proc/meminfo`
- Recalculates metrics
- Updates STATE_DB snapshot

- **T=10** - Third poll...
- (continues every 5 seconds)

**Key Considerations**

- **System-Level Only:** Single memory snapshot for entire system (not per-process or per-core)
- **Current Snapshot Only:** No average or historical data maintained for FR-3
- **MemAvailable vs MemFree:** Uses MemAvailable for more accurate available memory estimation
- **Unit Consistency:** All values stored in Bytes (raw). Converted to KB by the Management Interfaces for flexibility
- **Non-Persistent:** Snapshot resets on daemon restart
- **Lightweight Operation:** Minimal performance impact with 5-second polling

**History (FR-4):**

Same circular-buffer mechanism as CPU history, Each interval the daemon stores the total, used, available and average memory utilization percentage.

##### 5.2.3 Storage/Disk Utilization Monitoring

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

**7. Performance Optimization Considerations**

**7.1 Execution Strategy**

- **Polling Interval:** 5 seconds (configurable via DEFAULT_SRM_POLLING_INTERVAL_SECS)
- **Execution Model:** Sequential processing - statvfs() calls executed serially per partition
- **Resource Impact:** Minimal - lightweight read operations on sysfs, proc filesystems, and statvfs() system calls

**7.2 Caching and Efficiency**

- **Device Discovery Cache:** Device-to-partition mappings discovered once during daemon initialization and reused across cycles
- **Per-Cycle Execution:** Each monitoring cycle uses cached device mappings, only calls statvfs() for runtime data
- **File Reading:**  Standard Python file I/O with default buffering for /proc/mounts and sysfs reads

**7.3 Concurrency Considerations**

- **Single-threaded:** All operations execute sequentially in main daemon loop
- **Non-blocking:** Daemon uses event-based waiting (stop_event.wait()) between cycles
- **Lock-free reads:** No locking required - all data sources are read-only

##### 5.2.4 Threshold-Based Alarming

Three independent thresholds are supported:

- **CPU** - CONFIG_DB Key: `CPU_GLOBAL|global` - Field: `cpu_utilization_threshold`- Default: 85% 
- **Memory** - CONFIG_DB Key: `RAM_GLOBAL|global` field:`ram_utilization_threshold` - Default: 80% 
- **Disk** - CONFIG_DB Key: `STORAGE_GLOBAL|global, Field: `storage_utilization_threshold` - Default: 75% 

**Alarm lifecycle:**
      current >= threshold
CLEARED ─────────────────────────► ACTIVE
  ▲                                   │
  │        current < threshold        │
  └───────────────────────────────────┘

**Alarm Transitions:**

- **On transition CLEARED → ACTIVE:** Update `alarm_status` field to `active` in `CPU_TABLE` in STATE_DB, emit syslog `LOG_CRIT`
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

##### 5.2.5 Syslog Notifications

All threshold events produce syslog entries via the Python `syslog` module:

**Alarm raised (one syslog entries emitted per resource, at LOG_CRIT):**

**CPU**
<CRIT> pmon#platformd: ALARM RAISED: CPU_UTILIZATION | Resource: 0|0 | Current: 9% | Threshold: 2% | CPU utilization exceeded threshold 

<CRIT> pmon#platformd: ALARM RAISED: CPU_UTILIZATION | Resource: 0|1 | Current: 7% | Threshold: 2% | CPU utilization exceeded threshold 

**RAM**
<CRIT> pmon#platformd: ALARM RAISED: RAM_UTILIZATION | Current: 48% | Threshold: 5% | RAM utilization exceeded threshold 

**Alarm cleared (one syslog entries emitted per resource, at LOG_INFO):**

**CPU**
<INFO> pmon#platformd: ALARM CLEARED: CPU_UTILIZATION | Resource: 0|0 | Current: 35% | Threshold: 90% | CPU utilization returned to normal

<INFO> INFO pmon#platformd: ALARM CLEARED: CPU_UTILIZATION | Resource: 0|1 | Current: 35% | Threshold: 90% | CPU utilization returned to normal

**RAM**
<INFO> pmon#platformd: ALARM CLEARED: RAM_UTILIZATION | Current: 47% | Threshold: 90% | RAM utilization returned to normal 

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

#### 5.3 Target Deployment Use Cases
1. **Network Operations Center (NOC) Monitoring** — Operators query real-time and historical CPU/memory metrics to diagnose control-plane performance issues.
2. **Capacity Planning** — Historical utilization data helps architects right-size platforms.
3. **Proactive Alerting** — Threshold alarms trigger syslog messages consumed by external NMS/SIEM systems for early anomaly detection.
4. **Hardware Health Dashboards** — CPU, RAM, and Storage metrics feed into dashboards for platform resource monitoring

#### 5.4 Scalability Requirements

- The feature shall support systems with up to **128 logical CPU cores**.
- The feature shall dynamically discover and monitor all permanently attached storage partitions from `/proc/mounts` without limit restrictions.
- History circular buffer: max entries = `cpu_history_duration  / cpu_history_measurement_interval` per core (default 12 entries per core for CPU; 12 entries for memory)

#### 5.4.1 Redis Memory Footprint Estimation

Assumptions for a system with **128 logical CPU cores** (per-key size measured at 2 cores, extrapolated to 128), default history settings (duration=60 min, interval=5 min → 12 entries), and 10 storage partitions.

| STATE_DB Table                      | Keys                                 | Estimated Size per Key | Total       |
|-------------------------------------|--------------------------------------|------------------------|-------------|
| `CPU_GLOBAL`                        | 1                                    | ~19 Bytes              | ~0.02 KB    |
| `CPU_TABLE`                         | 128                                  | ~34 Bytes              | ~4.3 KB     |
| `CPU_HISTORY_TABLE`                 | 128 × 12 = 1,536                     | ~47 Bytes              | ~72 KB      |
| `RAM_GLOBAL`                        | 1                                    | ~19 Bytes              | ~0.02 KB    |
| `RAM_HISTORY_TABLE`                 | 12                                   | ~52 Bytes              | ~0.6 KB     |
| `STORAGE_TABLE`                     | 10                                   | ~78 Bytes              | ~0.8KB      |
| `STORAGE_INFO`                      | 3                                    | ~18 Bytes              | ~0.05 KB    |
| **Total**                           |                                      |                        | **~100 KB** |

With maximum configurable history (duration=180 min, interval=1 min → 180entries):

| Table                               | Keys                 | Total      |
|-------------------------------------|----------------------|------------|
| `CPU_HISTORY_TABLE`                 | 128 × 180 = 23040    | ~53 B      |
| `RAM_HISTORY_TABLE`                 | 180                  | ~43 B      |
| **Total (max config)**              |                      | **~96 MB** |

This is within acceptable Redis memory bounds. A validation warning should be emitted if the operator configures very large history windows on systems with many cores.

##### 5.4.2 CPU/RAM/STORAGE Overhead

| Operation                               | Frequency        | Estimated CPU Time |
|-----------------------------------------|------------------|------------ -------|
| Read `/proc/stat` (128 cores)           | Every 5 seconds  | < 1 ms             |
| Read `/proc/meminfo`                    | Every 5 seconds  | < 0.5 ms           |
| `os.statvfs()` × 10 partitions          | Every 5 seconds  | < 2 ms             |
| History write (128 cores × 1 entries)   | Every 5 minutes  | < 50 ms            |
| Threshold evaluation                    | Every 5 seconds  | < 1 ms             |
| **Total per cycle**                     |                  | **< 5 ms**         |

The daemon consumes negligible CPU resources (< 0.1 % of a single core).

### 6. Architecture Design

**platformmond Architecture diagram flow:**

┌─────────────────────────────────────────────────────────┐
│                Management Layer                         │
│                    (CLI)                                │
└────────────────────┬────────────────────────────────────┘
                     │ read thresholds / history config
┌────────────────────▼────────────────────────────────────┐
│                        CONFIG_DB                        │
│  CPU_GLOBAL|global                                      │
│  ├── cpu_utilization_threshold    (default: 85)         │
│  ├── cpu_history_measurement_interval (default: 5 min)  │
│  ├── cpu_history_duration         (default: 60 min)     │
│  └── history_status               (default: disabled)   │
│                                                         │
│  RAM_GLOBAL|global                                      │
│  ├── ram_utilization_threshold    (default: 80)         │
│  ├── ram_history_measurement_interval (default: 5 min)  │
│  ├── ram_history_duration         (default: 60 min)     │
│  └── history_status               (default: disabled)   │
└────────────────────┬────────────────────────────────────┘
                     │ read on startup + every 5s poll
┌────────────────────▼────────────────────────────────────┐
│                   PMON Container                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │                   platformmond                    │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Thread 1: CPU Snapshot (every 5s)          │  │  │
│  │  │  - Reads /proc/stat                         │  │  │
│  │  │  - Computes per-core utilization %          │  │  │
│  │  │    using total_delta and idle_delta         │  │  │
│  │  │  - Checks alarm threshold                   │  │  │
│  │  │  - Writes CPU_TABLE|{cpu}|{core}            │  │  │
│  │  │  - Polls CONFIG_DB for config changes       │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Thread 2: CPU History (every N min)        │  │  │
│  │  │  - Computes per-core utilization over       │  │  │
│  │  │       the measurement interval              │  │  │
│  │  │  - Evicts oldest if >= max_history_entries  │  │  │
│  │  │  - Writes CPU_HISTORY_TABLE|{cpu}|{core}    │  │  │
│  │  │              |{timestamp}                   │  │  │
│  │  │  - Clears per-core sample list              │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Thread 3: RAM Snapshot (every 5s)          │  │  │
│  │  │  - Reads /proc/meminfo                      │  │  │
│  │  │  - Computes total/used/available/util%      │  │  │
│  │  │  - Checks alarm threshold                   │  │  │
│  │  │  - Writes RAM_GLOBAL|global                 │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Thread 4: RAM History (every N min)        │  │  │
│  │  │  - Computes RAM utilization over the        │  │  │
│  │  │        measurement interval                 │  │  │
│  │  │  - Evicts oldest if >= max_history_entries  │  │  │
│  │  │  - Writes RAM_HISTORY_TABLE|{timestamp}     │  │  │
│  │  │  - Clears per-interval sample list          │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  AlarmManager (shared by Thread 1 & 3)      │  │  │
│  │  │  - Two-state machine: cleared ↔ active      │  │  │
│  │  │  - threshold == 0 → alarm Cleared           │  │  │
│  │  │  - Raise: LOG_ALERT + LOG_WARNING (syslog)  │  │  │
│  │  │  - Clear: LOG_INFO  + LOG_INFO   (syslog)   │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ writes
┌────────────────────▼────────────────────────────────────┐
│                      STATE_DB                           │
│                                                         │
│  CPU_TABLE|{cpu_index}|{core_index}                     │
│  ├── cpu_utilization                                    │
│  ├── alarm_status                                       │
│  └── timestamp                                          │
│                                                         │
│  CPU_HISTORY_TABLE|{cpu_index}|{core_index}|{timestamp} │
│  └── cpu_history_utilization                            │
│                                                         │
│  RAM_GLOBAL|global                                      │
│  ├── total_memory / used_memory / available_memory      │
│  ├── memory_utilization                                 │
│  ├── alarm_status                                       │
│  └── timestamp                                          │
│                                                         │
│  RAM_HISTORY_TABLE|{timestamp}                          │
│  └── memory_utilization                                 │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                     Syslog                              │
│  ALARM RAISED: LOG_ALERT  + LOG_WARNING (structured)    │
│  ALARM CLEARED: LOG_INFO  + LOG_INFO   (structured)     │
└─────────────────────────────────────────────────────────┘

**stormond Architecture diagram flow:**

┌─────────────────────────────────────────────────────────┐
│                    Management Layer                     │
│                         (CLI)                           │
└────────────────────┬────────────────────────────────────┘
                     │ read threshold config
┌────────────────────▼────────────────────────────────────┐
│                        CONFIG_DB                        │
│  STORAGE_GLOBAL|global                                  │
│  └── storage_utilization_threshold  (default: 75)       │
└────────────────────┬────────────────────────────────────┘
                     │ read on startup
┌────────────────────▼────────────────────────────────────┐
│                   PMON Container                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │                    stormond                       │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Startup: Device Discovery Pipeline         │  │  │
│  │  │  Stage 1: Parse /proc/mounts                │  │  │
│  │  │  Stage 2: Filter by device path pattern     │  │  │
│  │  │           (/dev/sd*, /dev/nvme*, etc.)      │  │  │
│  │  │  Stage 3: Exclude pseudo-filesystems        │  │  │
│  │  │           (tmpfs, devtmpfs, squashfs, etc.) │  │  │
│  │  │  Stage 4: Check /sys/block/*/removable      │  │  │
│  │  │           (exclude if removable == 1)       │  │  │
│  │  │  Stage 5: Select highest-priority mountpoint│  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Main Loop: Single-threaded (every 5s)      │  │  │
│  │  │                                             │  │  │
│  │  │  For each discovered partition:             │  │  │
│  │  │  - Call os.statvfs(mount_point)             │  │  │
│  │  │  - Compute total/used/available/util%       │  │  │
│  │  │  - Check alarm threshold                    │  │  │
│  │  │  - Write STORAGE_TABLE|{device}|{partition} │  │  │
│  │  │                                             │  │  │
│  │  │  No history collection                      │  │  │
│  │  │  No circular buffer                         │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  FSIO Counter Reconciliation                │  │  │
│  │  │  - Reads /proc/diskstats                    │  │  │
│  │  │  - Handles counter reset on reboot          │  │  │
│  │  │  - SoT: STATE_DB (crash) / JSON (reboot)    │  │  │
│  │  │  - Syncs to JSON daily                      │  │  │
│  │  │    (/usr/share/stormond/fsio-rw-stats.json) │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  AlarmManager                               │  │  │
│  │  │  - Two-state machine: cleared ↔ active      │  │  │
│  │  │  - threshold == 0 → alarm Cleared           │  │  │
│  │  │  - Raise: LOG_ALERT + LOG_WARNING (syslog)  │  │  │
│  │  │  - Clear: LOG_INFO  + LOG_INFO   (syslog)   │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  Signal Handler (SIGTERM/SIGINT)            │  │  │
│  │  │  - Flushes FSIO data to JSON before exit    │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
└──────────┬──────────────────────────┬───────────────────┘
           │ writes                   │ reads/writes
┌──────────▼──────────┐   ┌──────────▼──────────────────┐
│      STATE_DB       │   │  JSON Persistence File      │
│                     │   │  fsio-rw-stats.json         │
│  STORAGE_TABLE      │   │  - Total FSIO read bytes    │
│  |{device}          │   │  - Total FSIO write bytes   │
│  |{partition}       │   │  - Synced daily or on       │
│  ├── total_memory   │   │    graceful shutdown        │
│  ├── used_memory    │   └─────────────────────────────┘
│  ├── available_mem  │
│  ├── storage_util%  │
│  ├── alarm_status   │
│  └── timestamp      │
│                     │
│  STORAGE_INFO|*     │
│  ├── model          │
│  ├── serial         │
│  └── fs_type        │
└──────────┬──────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│                        Syslog                           │
│  ALARM RAISED:  LOG_ALERT  + LOG_WARNING (structured)   │
│  ALARM CLEARED: LOG_INFO   + LOG_INFO   (structured)    │
└─────────────────────────────────────────────────────────┘

#### 6.1 Basic Approach

Two Python daemons handle system resource monitoring, both running inside the **PMON container**.
A new Python daemon — **`platformmond`** — is introduced for this feature. It collects CPU and memory (RAM) metrics from the Linux kernel. It uses four independent threads — two snapshot threads (every 5 seconds) and two history threads (every configurable interval) — to collect current utilization and maintain historical averages in a circular buffer. It monitors configurable thresholds and raises/clears alarms via syslog. Alarm status is stored as a field within the respective resource tables (CPU_TABLE, RAM_GLOBAL) in STATE_DB.
**`stormond`** is an existing SONiC daemon that has been extended to support storage/disk partition monitoring as part of this feature. It runs a single-threaded main loop (every 5 seconds), discovers permanently attached storage devices via a multi-stage filtering pipeline (/proc/mounts, /sys/block/*/removable), and computes per-partition utilization using os.statvfs(). It monitors configurable thresholds and raises/clears alarms via syslog. Alarm status is stored within STORAGE_TABLE in STATE_DB. FSIO counters are persisted to a JSON file to survive reboots.

#### 6.2 Container

| Component                  | Location                                            |
|----------------------------|-----------------------------------------------------|
| `platformmond` , `stormond`| `pmon` container                                    |
| CLI                        | `sonic-cli` / Click framework                       |
| YANG                       | `sonic-mgmt-framework` container                    |

### 7 High-Level Design

#### 7.1 Overview

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              SONiC System                                 │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        pmon container                               │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                platformmond  (New Python daemon)             │   │  │
│  │  │                                                              │   │  │
│  │  │  ┌───────────────────────┐  ┌───────────────────────────┐    │   │  │
│  │  │  │  Thread 1 & 2:        │  │  Thread 3 & 4:            │    │   │  │
│  │  │  │  CPU Collector        │  │  RAM Collector            │    │   │  │
│  │  │  │  /proc/stat           │  │  /proc/meminfo            │    │   │  │
│  │  │  │  (snapshot: 5s)       │  │  (snapshot: 5s)           │    │   │  │
│  │  │  │  (history:  N min)    │  │  (history:  N min)        │    │   │  │
│  │  │  └──────────┬────────────┘  └─────────────┬─────────────┘    │   │  │
│  │  │             │                             │                  │   │  │
│  │  │             └──────────────┬──────────────┘                  │   │  │
│  │  │                            ▼                                 │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │              History Engine                         │     │   │  │
│  │  │  │  Circular buffer per core/resource per interval     │     │   │  │
│  │  │  │  Writes: CPU_HISTORY_TABLE, RAM_HISTORY_TABLE       │     │   │  │
│  │  │  └──────────────────────┬──────────────────────────────┘     │   │  │
│  │  │                         ▼                                    │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │           Threshold / Alarm Engine                  │     │   │  │
│  │  │  │  Compare current vs CONFIG_DB thresholds            │     │   │  │
│  │  │  │  Raise/clear alarms → syslog + CPU_TABLE/RAM_GLOBAL │     │   │  │
│  │  │  └─────────────────────────────────────────────────────┘     │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │              stormond  (Extended existing daemon)            │   │  │
│  │  │                                                              │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │  Device Discovery Pipeline (startup)                │     │   │  │
│  │  │  │  /proc/mounts → filter → /sys/block/*/removable     │     │   │  │
│  │  │  └──────────────────────┬──────────────────────────────┘     │   │  │
│  │  │                         ▼                                    │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │  Storage Collector — Single-threaded (every 5s)     │     │   │  │
│  │  │  │  os.statvfs() per partition                         │     │   │  │
│  │  │  │  Writes: STORAGE_TABLE                              │     │   │  │
│  │  │  └──────────────────────┬──────────────────────────────┘     │   │  │
│  │  │                         ▼                                    │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │  FSIO Counter Reconciliation                        │     │   │  │
│  │  │  │  /proc/diskstats → STATE_DB + JSON persistence      │     │   │  │
│  │  │  │  Handles counter reset on reboot                    │     │   │  │
│  │  │  └──────────────────────┬──────────────────────────────┘     │   │  │
│  │  │                         ▼                                    │   │  │
│  │  │  ┌─────────────────────────────────────────────────────┐     │   │  │
│  │  │  │           Threshold / Alarm Engine                  │     │   │  │
│  │  │  │  Compare current vs CONFIG_DB thresholds            │     │   │  │
│  │  │  │  Raise/clear alarms → syslog + STORAGE_TABLE        │     │   │  │
│  │  │  └─────────────────────────────────────────────────────┘     │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                  │                                        │
│                                  ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                     Redis (STATE_DB)                               │   │
│  │                                                                    │   │
│  │  platformmond writes:                  stormond writes:            │   │
│  │  • CPU_TABLE|{cpu}|{core}           • STORAGE_TABLE|{dev}|{part}   │   │
│  │  • CPU_HISTORY_TABLE|{cpu}|         • STORAGE_INFO|{device}        │   │
│  │      {core}|{timestamp}                                            │   │
│  │  • RAM_GLOBAL|global                                               │   │
│  │  • RAM_HISTORY_TABLE|{timestamp}                                   │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                     Redis (CONFIG_DB)                              │   │
│  │  • CPU_GLOBAL|global                                               │   │
│  │  • RAM_GLOBAL|global                                               │   │
│  │  • STORAGE_GLOBAL|global                                           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                ▲                                          │
│                                │                                          │
│  ┌─────────────────────────────┴───────────────────────────────────────┐  │
│  │              sonic-mgmt-framework container                         │  │
│  │                   YANG transformer                                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                          │
│                                │                                          │
│  ┌─────────────────────────────┴───────────────────────────────────────┐  │
│  │                    Click CLI (sonic-cli)                            │  │
│  │                                                                     │  │
│  │  show:   platform cpu | cpu-history | ram | ram-history | storage   │  │
│  │  config: platform cpu | cpu-history | ram | ram-history | storage   │  │
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
cpu_utilization_threshold        = 1*3DIGIT   ; percentage (0-100), default "85"
history_status                   = "enabled" / "disabled" ; default "disabled"
cpu_history_measurement_interval = 1*3DIGIT   ; minutes, default "5"
cpu_history_duration     = 1*4DIGIT    ; minutes, default "60"
```

Example:
```json
{
  "CPU_GLOBAL|global": {
    "cpu_utilization_threshold":        "85",
    "history_status":                   "disabled",
    "cpu_history_measurement_interval": "5",
    "cpu_history_duration":             "60"
  }
}

**Table: RAM_GLOBAL**

```
; Key
RAM_GLOBAL|global

; Fields
ram_history_measurement_interval = 1*3DIGIT           ; minutes, default "5"
ram_history_duration             = 1*4DIGIT           ; minutes, default "60"
history_status                   = "enabled" / "disabled"  ; default "disabled"
ram_utilization_threshold        = 1*3DIGIT           ; percentage (0-100), default "80"

```

Example:
```json
{
  "RAM_GLOBAL|global": {
    "ram_history_measurement_interval": "5",
    "ram_history_duration": "60",
    "history_status": "disabled",
    "ram_utilization_threshold": "80"
  }
}
```
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

```

**Table: RAM_GLOBAL**

Current snapshot of system memory.

```
; Key format
RAM_GLOBAL|global

; Fields
total_memory        = 1*20DIGIT                  ; bytes
used_memory         = 1*20DIGIT                  ; bytes
available_memory    = 1*20DIGIT                  ; bytes
memory_utilization  = 1*3DIGIT                   ; percentage (0-100)
alarm_status        = "active" / "cleared"
timestamp           = ISO-8601                   ; YYYY-MM-DDTHH:MM:SSZ
```

**Table: RAM_HISTORY_TABLE**

Historical average memory utilization.

```
; Key format
RAM_HISTORY_TABLE|<timestamp>
; where <timestamp> = ISO-8601 (YYYY-MM-DDTHH:MM:SSZ)

; Fields
timestamp           = ISO-8601                   ; YYYY-MM-DDTHH:MM:SSZ
total_memory        = 1*20DIGIT                  ; bytes (average)
used_memory         = 1*20DIGIT                  ; bytes (average)
available_memory    = 1*20DIGIT                  ; bytes (average)
memory_utilization  = 1*3DIGIT                   ; percentage (average)
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

#### 7.3 Flow Diagrams

##### 7.3.1 Resource Collection Flow

```
**platformmond**
                    ┌─────────────────────────┐
                    │        platformmond     │
                    │        (startup)        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Load CPU & RAM config  │
                    │  from CONFIG_DB         │
                    │  (CPU_GLOBAL,RAM_GLOBAL)│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Discover CPU cores     │
                    │  from /proc/stat        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼─────────────────────────────────┐
                    │  Clear CPU/RAM history in STATE_DB           │
                    │  ONLY if history transitions disabled→enabled│
                    └────────────┬─────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Start 4 threads       │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          │                      │                      │
┌─────────▼──────────┐           │           ┌──────────▼─────────┐
│  Thread 1:         │           │           │  Thread 3:         │
│  CPU Snapshot      │           │           │  RAM Snapshot      │
│  (every 5s)        │           │           │  (every 5s)        │
│                    │           │           │                    │
│  Read /proc/stat   │           │           │  Read /proc/meminfo│
│  Compute util%     │           │           │  Compute util%     │
│  per core          │           │           │                    │
│                    │           │           │                    │
│  Check alarm       │           │           │  Check alarm       │
│  threshold         │           │           │  threshold         │
│  (every poll)      │           │           │  (every poll)      │
│                    │           │           │                    │
│  Write CPU_TABLE   │           │           │  Write RAM_GLOBAL  │
│                    │           │           │                    │
│  Poll CONFIG_DB    │           │           │                    │
│  for threshold     │           │           │                    │
│  changes           │           │           │                    │
│  (interval/duration│           │           │                    │
│  only if disabled) │           │           │                    │
└────────────────────┘           │           └────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                                             │
┌─────────▼──────────┐                       ┌──────────▼─────────┐
│  Thread 2:         │                       │  Thread 4:         │
│  CPU History       │                       │  RAM History       │
│  (every N min)     │                       │  (every N min)     │
│                    │                       │                    │
│  Evict oldest if   │                       │  Evict oldest if   │
│  >=max_entries     │                       │  >=max_entries     │
│  from buffer+DB    │                       │  from buffer+DB    │
│                    │                       │                    │
│  Write             │                       │  Write             │
│  CPU_HISTORY_TABLE │                       │  RAM_HISTORY_TABLE │
│                    │                       │                    │
│  Clears per-core   │                       │  Clears per-core   │
│     sample list    │                       │  sample list       │
└────────────────────┘                       └────────────────────┘

          All threads → AlarmManager (shared)
          ┌─────────────────────────────────┐
          │  Two-state: cleared ↔ active    │
          │  threshold == 0 → disabled      │
          │  Raise: LOG_ALERT + LOG_WARNING │
          │  Clear: LOG_INFO  + LOG_INFO    │
          └─────────────────────────────────┘
  
**stormond**

                    ┌─────────────────────────┐
                    │        stormond         │
                    │        (startup)        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Load storage config    │
                    │  from CONFIG_DB         │
                    │  (STORAGE_GLOBAL)       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Device Discovery       │
                    │  Pipeline               │
                    │                         │
                    │  Stage 1: /proc/mounts  │
                    │  Stage 2: Filter device │
                    │    path patterns        │
                    │    (sd*, nvme*, etc.)   │
                    │  Stage 3: Exclude       │
                    │    pseudo-filesystems   │
                    │    (tmpfs, squashfs..)  │
                    │  Stage 4: Check         │
                    │    /sys/block/*/        │
                    │    removable            │
                    │  Stage 5: Select        │
                    │    highest-priority     │
                    │    mount point          │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  FSIO Counter           │
                    │  Reconciliation         │
                    │                         │
                    │  Determine SoT:         │
                    │  INIT / STATE_DB /      │
                    │  JSON                   │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │    Single-threaded Main Loop (5s)   │
              │                                     │
              │  For each discovered partition:     │
              │  ┌───────────────────────────────┐  │
              │  │  Call os.statvfs(mount_point) │  │
              │  │  Compute total/used/avail/%   │  │
              │  └──────────────┬────────────────┘  │
              │                 │                   │
              │  ┌──────────────▼────────────────┐  │
              │  │  Check alarm threshold        │  │
              │  │  (every poll)                 │  │
              │  │                               │  │
              │  │  current >= threshold?        │  │
              │  │  → raise alarm (LOG_ALERT     │  │
              │  │    + LOG_WARNING)             │  │
              │  │  current < threshold?         │  │
              │  │  → clear alarm (LOG_INFO      │  │
              │  │    + LOG_INFO)                │  │
              │  └──────────────┬────────────────┘  │
              │                 │                   │
              │  ┌──────────────▼────────────────┐  │
              │  │  Write STORAGE_TABLE          │  │
              │  │  (snapshot + alarm_status)    │  │
              │  └──────────────┬────────────────┘  │
              │                 │                   │
              │  ┌──────────────▼────────────────┐  │
              │  │  Update FSIO counters         │  │
              │  │  from /proc/diskstats         │  │
              │  └──────────────┬────────────────┘  │
              │                 │                   │
              │  ┌──────────────▼────────────────┐  │
              │  │  Sync interval elapsed?       │  │
              │  │  → Flush FSIO to JSON file    │  │
              │  └───────────────────────────────┘  │
              │                                     │
              │     sleep(5 seconds)                │
              │     loop ↑                          │
              └─────────────────────────────────────┘

                       On SIGTERM/SIGINT:
                ┌─────────────────────────────────┐
                │  Flush FSIO counters to JSON    │
                │  before exit                    │
                └─────────────────────────────────┘
```

##### 7.3.2 Threshold Alarm Flow

```
    ┌──────────────────┐        ┌──────────────────┐
    │  Daemon collects │        │  threshold == 0? │
    │  current metric  │───────▶│                 │
    │  (CPU/RAM/Disk)  │        └────────┬─────────┘
    └──────────────────┘                 │
                               YES       │    NO
                         ┌───────────────┘    │
                         ▼                    ▼
                ┌─────────────────┐  ┌────────────────────┐
                │ Alarm disabled  │  │  Compare current   │
                │ force cleared   │  │  with threshold    │
                └─────────────────┘  └─────────┬──────────┘
                                               │
                          ┌────────────────────┤
                          │                    │
              ┌───────────▼──────────┐  ┌──────▼───────────────┐
              │ current >= threshold │  │ current < threshold  │
              │ AND prev = cleared   │  │ AND prev = active    │
              └───────────┬──────────┘  └──────┬───────────────┘
                          │                    │
              ┌───────────▼──────────┐  ┌──────▼───────────────┐
              │  Set alarm = active  │  │  Set alarm = cleared │
              │  Write STATE_DB      │  │  Write STATE_DB      │
              │  syslog LOG_ALERT    │  │  syslog LOG_INFO     │
              │  syslog LOG_WARNING  │  │  syslog LOG_INFO     │
              │  (structured)        │  │  (structured)        │
              └──────────────────────┘  └──────────────────────┘
```


#### 7.4 Sequence Diagram

**Sequence 1a: platformmond Initialization**
```
┌──────┐    ┌────────────┐       ┌───────────┐       ┌──────────┐
│ PMON │    │platformmond│       │ CONFIG_DB │       │ STATE_DB │
└──┬───┘    └────┬───────┘       └─────┬─────┘       └────┬─────┘
   │             │                     │                  │
   │ Start       │                     │                  │
   │ platformmond│                     │                  │
   ├────────────>│                     │                  │
   │             │                     │                  │
   │             │ Read CPU_GLOBAL     │                  │
   │             ├────────────────────>│                  │
   │             │                     │                  │
   │             │ Read RAM_GLOBAL     │                  │
   │             ├────────────────────>│                  │
   │             │                     │                  │
   │             │ CPU & RAM thresholds│                  │
   │             │ & history config    │                  │
   │             │<────────────────────┤                  │
   │             │                     │                  │
   │             │ Discover CPU cores  │                  │
   │             │ from /proc/stat     │                  │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Read CPU_GLOBAL &   │                  │
   │             │ RAM_GLOBAL history  │                  │
   │             │ status from         │                  │
   │             ├────────────────────────────────────────>
   │             │                     │                  │
   │             │ Clear CPU/RAM history (only if         │
   │             │ history transitions disabled→enabled)  │
   │             ├────────────────────────────────────────>
   │             │                     │                  │
   │             │ Start Thread 1: CPU snapshot (5s)      │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Start Thread 2: CPU history (N min)    │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Start Thread 3: RAM snapshot (5s)      │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Start Thread 4: RAM history (N min)    │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │   Ready     │                     │                  │
   │<────────────┤                     │                  │
   
```

**Sequence 1b: stormond Initialization**
```
┌──────┐    ┌──────────┐         ┌───────────┐       ┌──────────┐
│ PMON │    │ stormond │         │ CONFIG_DB │       │ STATE_DB │
└──┬───┘    └────┬─────┘         └─────┬─────┘       └────┬─────┘
   │             │                     │                  │
   │ Start       │                     │                  │
   │ stormond    │                     │                  │
   ├────────────>│                     │                  │
   │             │                     │                  │
   │             │ Read STORAGE_GLOBAL │                  │
   │             ├────────────────────>│                  │
   │             │                     │                  │
   │             │ Storage threshold   │                  │
   │             │<────────────────────┤                  │
   │             │                     │                  │
   │             │ Device Discovery Pipeline              │
   │             │ Stage 1: Parse /proc/mounts            │
   │             │ Stage 2: Filter device path patterns   │
   │             │ Stage 3: Exclude pseudo-filesystems    │
   │             │ Stage 4: Check /sys/block/*/removable  │
   │             │ Stage 5: Select highest-priority mount │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ FSIO Counter Reconciliation            │
   │             │ Read existing STATE_DB FSIO values     │
   │             ├────────────────────────────────────────>
   │             │                     │                  │
   │             │ Read JSON persistence file             │
   │             │ (fsio-rw-stats.json)│                  │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Determine SoT:      │                  │
   │             │ INIT / STATE_DB /   │                  │
   │             │ JSON                │                  │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │             │ Start single-threaded main loop (5s)   │
   │             │──┐                  │                  │
   │             │  │                  │                  │
   │             │<─┘                  │                  │
   │             │                     │                  │
   │   Ready     │                     │                  │
   │<────────────┤                     │                  │

```

**Sequence 2a: platformmond Metric Collection and Threshold Monitoring**

```
┌─────────────┐ ┌───────────┐  ┌────────┐  ┌────────┐
│ platformmond│ │  Linux    │  │STATE_DB│  │ Syslog │
│(4 threads)  │ │  Kernel   │  │        │  │        │
└─────┬───────┘ └─────┬─────┘  └───┬────┘  └───┬────┘
      │               │            │           │
      │ [Thread 1: CPU Snapshot - every 5s]    │
      │               │            │           │
      │ Read /proc/stat            │           │
      ├──────────────>│            │           │
      │               │            │           │
      │ CPU jiffy data│            │           │
      │<──────────────┤            │           │
      │               │            │           │
      │ Compute per-core util%     │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ Check alarm:  │            │           │
      │ current >= threshold?      │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ [If alarm state changes]   │           │
      │               │            │           │
      │ Alarm raised: │            │           │
      ├───────────────────────────────────────>│
      │ LOG_ALERT (human-readable) │           │
      │ LOG_WARNING (structured)   │           │
      │               │            │           │
      │ Alarm cleared:│            │           │
      ├───────────────────────────────────────>│
      │ LOG_INFO (human-readable)  │           │
      │ LOG_INFO (structured)      │           │
      │               │            │           │
      │ Write CPU_TABLE|{cpu}|{core}           │
      │ (util%, alarm_status,      │           │
      │  timestamp)   │            │           │
      ├──────────────────────────>│            │
      │               │            │           │
      │ Poll CONFIG_DB for         │           │
      │ threshold changes          │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ [Thread 3: RAM Snapshot - every 5s]    │
      │               │            │           │
      │ Read /proc/meminfo         │           │
      ├──────────────>│            │           │
      │               │            │           │
      │ MemTotal, MemAvailable     │           │
      │<──────────────┤            │           │
      │               │            │           │
      │ Compute total/used/        │           │
      │ available/util%            │           │
      │               │            │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ Check alarm:  │            │           │
      │ current >= threshold?      │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ [If alarm state changes]   │           │
      │               │            │           │
      │ Alarm raised: │            │           │
      ├───────────────────────────────────────>│
      │ LOG_ALERT (human-readable) │           │
      │ LOG_WARNING (structured)   │           │
      │               │            │           │
      │ Alarm cleared:│            │           │
      ├───────────────────────────────────────>│
      │ LOG_INFO (human-readable)  │           │
      │ LOG_INFO (structured)      │           │
      │               │            │           │
      │ Write RAM_GLOBAL|global    │           │
      │ (total/used/avail/util%,   │           │
      │  alarm_status, timestamp)  │           │
      ├──────────────────────────>│            │
      │               │            │           │
      │ [Thread 2: CPU History - every N min]  │
      │               │            │           │
      │ Evict oldest if            │           │
      │ >= max_history_entries     │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ Write CPU_HISTORY_TABLE    │           │
      │ |{cpu}|{core}|{timestamp}  │           │
      ├──────────────────────────>│            │
      │               │            │           │
      │ Clear per-core sample list │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ [Thread 4: RAM History - every N min]  │
      │               │            │           │
      │ Evict oldest if            │           │
      │ >= max_history_entries     │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ Write RAM_HISTORY_TABLE    │           │
      │ |{timestamp}  │            │           │
      ├──────────────────────────> │           │
      │               │            │           │
      │ Clear sample list          │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │

```

**Sequence 2b: stormond Metric Collection and Threshold Monitoring**

```
┌────────────┐  ┌───────────┐  ┌────────┐  ┌────────┐
│  stormond  │  │  Linux    │  │STATE_DB│  │ Syslog │
│(single     │  │  Kernel   │  │        │  │        │
│ threaded)  │  │           │  │        │  │        │
└─────┬──────┘  └─────┬─────┘  └───┬────┘  └───┬────┘
      │               │            │           │
      │ [Main Loop - every 5s]     │           │
      │               │            │           │
      │ For each discovered partition:         │
      │               │            │           │
      │ os.statvfs(mount_point)    │           │
      ├──────────────>│            │           │
      │               │            │           │
      │ f_blocks, f_bfree,         │           │
      │ f_bavail, f_frsize         │           │
      │<──────────────┤            │           │
      │               │            │           │
      │ Compute total/used/        │           │
      │ available/util%            │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ Check alarm:  │            │           │
      │ current >= threshold?      │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ [If alarm state changes]   │           │
      │               │            │           │
      │ Alarm raised: │            │           │
      ├───────────────────────────────────────>│
      │ LOG_ALERT (human-readable) │           │
      │ LOG_WARNING (structured)   │           │
      │               │            │           │
      │ Alarm cleared:│            │           │
      ├───────────────────────────────────────>│
      │ LOG_INFO (human-readable)  │           │
      │ LOG_INFO (structured)      │           │
      │               │            │           │
      │ Write STORAGE_TABLE        │           │
      │ |{device}|{partition}      │           │
      │ (total/used/avail/util%,   │           │
      │  alarm_status, timestamp)  │           │
      ├──────────────────────────> │           │
      │               │            │           │
      │ Update FSIO counters       │           │
      │ from /proc/diskstats       │           │
      ├──────────────>│            │           │
      │               │            │           │
      │ FSIO read/write bytes      │           │
      │<──────────────┤            │           │
      │               │            │           │
      │ Sync interval elapsed?     │           │
      │ Flush FSIO to JSON file    │           │
      │──┐            │            │           │
      │  │            │            │           │
      │<─┘            │            │           │
      │               │            │           │
      │ sleep(5s) → loop ↑         │           │

```

**Sequence 3: History Data Collection**

```
┌──────────────┐     ┌──────────┐     ┌───────────┐
│ platformmond │     │ STATE_DB │     │ CONFIG_DB │
│ (Thread 2:   │     │          │     │           │
│  CPU History │     │          │     │           │
│  Thread 4:   │     │          │     │           │
│  RAM History)│     │          │     │           │
└──────┬───────┘     └────┬─────┘     └─────┬─────┘
       │                  │                 │
       │ [One-time at startup]              │
       │                  │                 │
       │ Read CPU_GLOBAL & RAM_GLOBAL       │
       │ history config                     │
       ├───────────────────────────────────>│
       │                  │                 │
       │ cpu/ram_history_duration,          │
       │ cpu/ram_history_measurement_       │
       │ interval                           │
       │<───────────────────────────────────┤
       │                  │                 │
       │ Calculate:       │                 │
       │ max_history_entries =              │
       │ history_duration //                │
       │ history_interval                   │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │ [Thread 2: CPU History]            │
       │ [Runs independently every N min]   │
       │                  │                 │
       │ Sleep(cpu_history_interval)        │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │ Evict oldest entry if              │
       │ len(buffer) >= max_history_entries │
       │ (remove from buffer + STATE_DB)    │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │ Write CPU_HISTORY_TABLE            │
       │ |{cpu_index}|{core_index}          │
       │ |{timestamp}     │                 │
       ├─────────────────>│                 │
       │                  │                 │
       │ Clear cpu_core sample list         │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │ [Thread 4: RAM History]            │
       │ [Runs independently every N min]   │
       │                  │                 │
       │ Sleep(ram_history_interval)        │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │                  │                 │
       │ Evict oldest entry if              │
       │ len(buffer) >= max_history_entries │
       │ (remove from buffer + STATE_DB)    │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
       │                  │                 │
       │ Write RAM_HISTORY_TABLE            │
       │ |{timestamp}     │                 │
       ├─────────────────>│                 │
       │                  │                 │
       │ Clear sample list│                 │
       │──┐               │                 │
       │  │               │                 │
       │<─┘               │                 │
```

### 8. Configuration and Management

- All configurations shall be persisted in CONFIG_DB and survive warm/cold reboot.
- History data (CPU, RAM) shall be stored in STATE_DB and is **not** required to survive restart.
- CLI (Click) interface is implemented for show and config commands.
- YANG models shall be provided for CONFIG_DB validation.

#### 8.1 Daemon Design

##### 8.1.1 platformmond

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
6. Discover logical CPU cores from /proc/stat.
7. Discover mounted storage partitions via os.statvfs().
8. Start 4 independent threads:
   - Thread 1: CPU snapshot (every 5s)
   - Thread 2: CPU history  (every cpu_history_interval minutes)
   - Thread 3: RAM snapshot (every 5s)
   - Thread 4: RAM history  (every ram_history_interval minutes)
9. Main thread waits on stop event (SIGTERM/SIGINT).

```

#### 8.1.4 stormond (Storage Monitoring Daemon)

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
1. Connect to CONFIG_DB and STATE_DB
2. Load SRM configuration from STORAGE_GLOBAL|global
3. Initialize legacy stormond components (storage device monitoring)
4. Discover permanent storage devices and partitions from /proc/mounts
5. Filter removable devices via /sys/block/*/removable
6. Initialize alarm manager
7. Enter main loop
```
#### 8.4 CLI

#### 8.2.1 Configuration Commands

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
```

#### 8.2.2 Show Commands

**Show CPU Utilization (Current-snapshot):**

```
admin@sonic:~$ show platform cpu
```

Output:
```
admin@sonic:~$ show platform cpu
 Cpu Index    Core Index    Utilization    Alarm Status    Threshold       Timestamp
-----------  ------------  -------------  --------------  -----------  -----------------
     0            0             4%           Cleared         20%       20260612 10:13:46
     0            1             4%           Cleared         20%       20260612 10:13:46
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
     0            0        20260603 04:03:46       5%
     0            0        20260603 04:08:46       5%
     0            0        20260603 04:13:46       5%
     0            0        20260603 04:18:46       5%
     0            0        20260603 04:23:46       5%
```

**Show Memory Utilization (Current-snapshot):**

```
admin@sonic:~$ show platform ram
```

Output:
```
 Total Memory    Used Memory    Available    Utilization    Alarm Status    Threshold       Timestamp
--------------  -------------  -----------  -------------  --------------  -----------  ------------------
  3945556 KB     1738704 KB    2206852 KB        44%          Cleared          80%      20260602 14:51:12
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
20260603 04:03:51    3945556 KB     1758676 KB    2186879 KB        44%
20260603 04:08:51    3945556 KB     1764160 KB    2181395 KB        44%
20260603 04:13:51    3945556 KB     1759789 KB    2185766 KB        44%
20260603 04:18:51    3945556 KB     1760426 KB    2185129 KB        44%
20260603 04:23:51    3945556 KB     1761242 KB    2184313 KB        44%
```

**Show Storage Utilization:**

```
admin@sonic:~$ show platform storage
```

Output:
```
 Device    Partition      Total        Used      Available    Utilization    Alarm Status    Threshold       Timestamp
--------  -----------  -----------  ----------  -----------  -------------  --------------  -----------  ------------------
  sda      /dev/sda3   16206120 KB  6897984 KB  9291752 KB      42.56%         Cleared          75%      20260602 14:50:55
```

**Show Active Alarms:**

```
admin@sonic:~$ show platform cpu
```

Output:
```
 Cpu Index    Core Index    Utilization    Alarm Status    Threshold       Timestamp
-----------  ------------  -------------  --------------  -----------  -----------------
     0            0             90%            Active          85%       20260612 10:13:46
     0            1             7%             Cleared         85%       20260612 10:13:46
```

```
admin@sonic:~$ show platform ram
```

Output:
```
 Total Memory    Used Memory    Available    Utilization    Alarm Status    Threshold       Timestamp
--------------  -------------  -----------  -------------  --------------  -----------  ------------------
  3945556 KB     3732208 KB     213348 KB        95%           Active          80%      20260603 05:19:37
```

```
admin@sonic:~$ show platform storage
```

Output:
```
 Device    Partition      Total        Used       Available    Utilization    Alarm Status    Threshold       Timestamp
--------  -----------  -----------  -----------  -----------  -------------  --------------  -----------  ------------------
  sda      /dev/sda3   16206120 KB  12645768 KB  3543968 KB      78.03%          Active          75%      20260603 05:23:10
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

### 8.3 YANG Model

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

#### 8.4 Error Handling

This section describes error handling organized by subsystem, with precise handling descriptions.

##### 8.4.1 Database Connection Errors

| Scenario                              | Handling                   | Log Level |
|---------------------------------------|----------------------------|--------- -|
|Database connection failure (startup)  |Exception raised in init(),daemon exits with sys.exit(1),upervisord restarts  |ERROR      |
|STATE_DB write failure                 |Caught in _update_cpu_snapshot_db(). Log ERROR: "Failed to update CPU snapshot DB: <str(e)>". Skip write, retry next cycle (5s). In-memory state retained. |ERROR    |
|STATE_DB write failure (RAM snapshot)  |Caught in _update_ram_snapshot_db(). Log ERROR: "Failed to update RAM snapshot DB: <str(e)>". Skip write, retry next cycle (5s). In-memory state retained. |ERROR    |
|STATE_DB write failure (CPU history)   |Caught in update_history(). Log ERROR: "Failed to update CPU history: <str(e)>". History entry lost for that interval; in-memory buffer still updated. Retry on next interval. |ERROR |
|STATE_DB write failure (RAM history)   |Caught in update_history(). Log ERROR: "Failed to update RAM history: <str(e)>". History entry lost for that interval; in-memory buffer still updated. Retry on next interval. |ERROR |

##### 8.4.2 Data Collection Errors

| Error Condition                                  | Handling                                      |Log Level |
|----------------------------------------------------------|-----------------------------------------------|----------|
|/proc/stat unreadable (file missing or permission denied) |Generic exception handler catches error. Log ERROR: "Failed to update CPU snapshot: <str(e)>". Skip current collection cycle for all cores. STATE_DB CPU_TABLE retains last written values; timestamp field not updated — consumers can detect staleness. Retry on next cycle (5s).| ERROR|
|/proc/stat missing steal field (len(parts) < 8)           | steal defaults to 0 via steal = int(parts[8]) if len(parts) > 8 else 0 guard. No explicit handling for missing required fields (user, nice, system, idle). If parts list is shorter than expected, int(parts[N]) raises IndexError. Generic exception handler in update_snapshot() catches and logs ERROR: "Failed to update CPU snapshot: <str(e)>". Cycle skipped for all cores.|ERROR |
|New CPU core appears between cycles (CPU hotplug)         | if core_name not in self.cpu_cores: continue — new cores silently skipped until daemon restart. No log entry generated.|Silent |
|/proc/meminfo unreadable (file missing or permission denied)| Generic exception handler catches error. Log ERROR: "Failed to update RAM snapshot: <str(e)>". Skip the current collection cycle for memory. Retry on the next cycle (5s). STATE_DB retains the last successfully written values; the timestamp field is not updated, allowing consumers to detect staleness.|ERROR |
|/proc/meminfo line parsing error                          | Line split by ':' checked via if len(parts) == 2. Lines not matching format are silently skipped. Value extraction wrapped in implicit safeguards — int(parts[1].strip().split()[0]) may raise ValueError or IndexError if malformed, caught by outer exception handler, logs ERROR, entire cycle skipped.|ERROR |

##### 8.4.3 Configuration Errors

| Error Condition                                     | Handling                                                                 |Log Level|
|----------------------------------------------|-------------------------------------------------------|----------------------------|
|CPU_GLOBAL, RAM_GLOBAL missing at startup     |Detected via if 'global' in keys check. Call _create_default_configuration() to write hardcoded defaults to CONFIG_DB. Log INFO: "Created default CPU/RAM configuration".|INFO |
|Invalid values in CONFIG_DB (non-integer, etc.|int() conversion called directly without try-except. ValueError propagates to outer exception handler in _check_configuration_changes(). Logs ERROR: "Failed to check CPU/RAM configuration: <str(e)>". Configuration values remain unchanged from previous valid state.|ERROR |
|history_status changed disabled → enabled     |Detected in _check_configuration_changes() via if new_status != self.history_enabled. Calls _clear_history_data() to clear buffers and STATE_DB entries. Updates flag. Logs INFO: "Cleared previous CPU/RAM history data on re-enable" and "CPU/RAM history status changed: False -> True".|INFO |

##### 8.4.5 Alarm Processing Errors

| Error Condition                      | Handling                           | Log Level|
|--------------------------------------|------------------------------------|----------|
| Invalid alarm values (non-numeric)   | No explicit validation of cpu_core.current_utilization or self.threshold before comparison. If non-numeric, if cpu_core.current_utilization >= self.threshold raises TypeError. Caught by outer try-except in update_snapshot(). Logs ERROR: "Failed to update CPU/RAM snapshot: <str(e)>". Alarm state unchanged (remains as last valid state).     | ERROR    |

##### 8.4.6 Daemon Lifecycle Errors

| Error Condition                 | Handling                           | Log Level|
|---------------------------------|------------------------------------|----------|
| SIGTERM/SIGINT received         | signal_handler() catches signal, logs INFO, raises KeyboardInterrupt. Main catches KeyboardInterrupt, calls platform_daemon.deinit(). Log INFO: "Received shutdown signal". Clean exit via finally block. | INFO   |
| Uncaught exception in main loop | Caught by outer except Exception as e: in main(). Logs ERROR: "Unhandled exception: <str(e)>". Exits with sys.exit(2). Supervisord detects non-zero exit and restarts after delay.| ERROR    |
| Daemon crash                    | Worker threads (_cpu_snapshot_worker, etc.) have individual try-except blocks. Thread-level exceptions logged as ERROR: "Error in CPU/RAM snapshot/history worker: <str(e)>". Thread continues running (does not crash). Main thread continues. No daemon restart unless main thread crashes.| ERROR      |

##### 8.4.7  Infrastructure Errors

|Error Condition                                     |Handling                                        |Log Level |
|----------------------------------------------------|------------------------------------------------|----------|
| STATE_DB unreachable during snapshot write         | Exception raised by swsscommon Table operations. Caught in _update_cpu_snapshot_db() or _update_ram_snapshot_db(). Logs ERROR: "Failed to update CPU/RAM snapshot DB: <str(e)>". Continue reading /proc/stat or /proc/meminfo in-memory; retry write on next cycle (5s). Every failed cycle produces a log entry (no suppression).|ERROR |
| Redis memory pressure or `OOM` condition           | No explicit handling. If swsscommon write fails due to memory, caught by exception handlers. Logs ERROR as above. In-memory history_buffer uses deque(maxlen=n) implicitly via manual management in update_history() — oldest removed before adding new when len() >= max_history_entries. Daemon does not cause memory pressure via unbounded growth.|ERROR |
| Multiple CPU cores exceed threshold simultaneously | Each core evaluated independently in sequential loop within update_snapshot(). _check_alarm(cpu_core) called once per core with resource_id = cpu_core.get_key() returning "{cpu_index}|{core_index}" composite key (e.g., "0|0", "0|1"). Separate alarm raised per core via AlarmManager.raise_alarm() — emits two syslog messages per core: human-readable at ALERT level, structured PLATFORM_ALARM: at WARNING level. Each core's alarm_status tracked independently in self.alarm_states dict. Each core's alarm cleared independently when its own utilization drops below threshold. No aggregate alarm exists — per-core granularity maintained throughout.|ERROR (for exceptions), WARNING (for syslog structured messages) |
| Syslog daemon (rsyslog) unavailable                | Daemon uses Python's syslog module directly in AlarmManager (syslog.syslog()). No explicit try-except around syslog calls. If /dev/log socket unavailable, behavior depends on Python's syslog implementation — may raise OSError (uncaught) or silently fail. No explicit OSError handling confirmed in AlarmManager code. Design assumption: logging failure should not block data collection or alarm evaluation — currently not enforced via exception handling. Note: No explicit syslog reconnection logic implemented — Python's syslog module manages socket internally. |ERROR | 
|STATE_DB unreachable during runtime                 | Same as "STATE_DB unreachable during snapshot write" — caught per write operation, logs ERROR, retries next cycle. |ERROR |
| Disk full (STATE_DB writes fail)                   | swsscommon write failures caught by exception handlers. Logs ERROR. Daemon continues read-only (monitoring /proc/stat, /proc/meminfo). Resumes writes when space available (next successful cycle).|ERROR |
| history_table._del() fails (removing oldest entry) | Called in update_history() when circular buffer full. Wrapped in outer try-except of update_history(). Logs ERROR: "Failed to update CPU/RAM history: <str(e)>". Entire history update aborted — new entry not added to STATE_DB, but still added to in-memory buffer (buffer update happens before DB write). Creates inconsistency between buffer and DB.  | ERROR       |

##### 8.4.8 CLI Errors

|Scenario                                                                    |  Handling |
|----------------------------------------------------------------------------|-----------|
| show platform cpu issued before daemon has completed first collection cycle| CPU_TABLE contains no entries in STATE_DB. CLI displays: "No CPU utilization data available. The monitoring daemon (platformmond) may still be initializing."
| show platform cpu-history with no history entries collected yet            | CLI displays: "No CPU history data available. History collection interval is <X> minutes; please wait for the first sample.
| show platform storage when no permanent partitions are discovered   | CLI displays: "No storage partitions found." Log LOG_WARNING — this is unexpected on any real system and may indicate a /proc/mounts parsing issue.
| sudo config platform cpu utilization-threshold <value> with out-of-range value (e.g., negative or 101)|  YANG range "0..100" constraint rejects the value,Daemon also validates range 0-100 in _check_configuration_changes() and logs LOG_ERR if invalid, providing defense-in-depth beyond YANG constraints.CLI returns: "Error: Invalid value <value>. CPU threshold must be between (0-100)." CONFIG_DB is not modified.
| show platform ram issued before daemon has completed first collection cycle| RAM_GLOBAL_TABLE in STATE_DB contains no snapshot fields — _update_ram_snapshot_db() has not yet been called. Within first 5 seconds (RAM_SNAPSHOT_POLLING_INTERVAL=5), total_memory, used_memory, available_memory, memory_utilization fields are absent.
| show platform ram-history with no history entries collected yet            | RAM_HISTORY_TABLE in STATE_DB contains no keys. _ram_history_worker() polls is_history_enabled() every 5 seconds — if history_enabled=False, no entries are written.
| config platform ram threshold <value> with out-of-range value              | Handled at management framework layer via YANG constraints before reaching CONFIG_DB. Daemon's _check_configuration_changes() reads ram_utilization_threshold via int() conversion — non-integer values raise ValueError, caught by generic except Exception as e, logs LOG_ERR: 'Failed to check ram configuration: <str(e)>', threshold unchanged.
| config platform  ram-history measurement-interval <value>                  | where value does not evenly divide duration No daemon-level validation of interval vs duration relationship. _calculate_max_history_entries() uses integer division duration // interval — non-zero result always produced. YANG must constraint is the only enforcement layer.
| CONFIG_DB Redis operations are atomic. _check_configuration_changes() is polled every update_snapshot() cycle (every 5 seconds) | not subscription-based. Last write to CONFIG_DB wins. Daemon reads full config on next poll cycle and applies final state.
| show platform storage when no permanent partitions exist on system         | CLI displays: "No storage partitions found." Log LOG_WARNING: "No permanent storage devices discovered. Check /proc/mounts and device filters."|
| config platform storage utilization-threshold <value> with out-of-range value (e.g., 0 or 100)  | YANG range constraint "0..100" rejects the value, aemon also validates range 0-100 in _check_configuration_changes() and logs LOG_ERR if invalid, providing defense-in-depth beyond YANG constraints. CLI returns: "Error: Invalid value. Storage threshold must be between (0-100)." CONFIG_DB not modified. |
| config platform storage utilization-threshold <value> where CONFIG_DB write fails |CLI logs LOG_ERROR: "Failed to update storage threshold in CONFIG_DB: <error>". Command fails. Daemon continues using previous threshold. Next restart reloads old threshold from CONFIG_DB.  |
| Partition unmounted between daemon cycles  |cycles - Next cycle removes from STATE_DB STORAGE_TABLE. Active alarm auto-cleared. Log LOG_NOTICE: "STORAGE ALARM CLEARED: <partition> - No longer mounted".|
| Partition mounted between daemon cycles |Next cycle adds to STATE_DB if qualifying. Log LOG_INFO: "Discovered new storage partition: <device>|<partition> at <mount_point>". |
| show platform storage while partition unmounting |CLI reads stale STATE_DB entry. Shows old data with old timestamp. Next cycle (5s) updates. No CLI crash — temporary inconsistency.  |

##### 8.5 Error Recovery Summary

The following diagram illustrates the daemon's error recovery state machine:

┌─────────────┐
│ supervisord │
│ starts      │
│ platformmond│
│ stormond    │
└──────┬──────┘
       │
       ├────────────────────────────────────────────────────────┐
       │                                                        │
┌──────▼──────┐    Exception        ┌──────────────┐    ┌───────▼──────┐    Exception        ┌──────────────┐
│platformmond │───in init()────────►│  sys.exit(1) │    │   stormond   │───in __init__()────►│  sys.exit(1) │
│   main()    │                     │  supervisord │    │   main()     │                     │  supervisord │
│   init()    │                     │  restarts    │    │   __init__() │                     │  restarts    │
└──────┬──────┘                     └──────────────┘    └──────┬───────┘                     └──────────────┘
       │ success                                               │ success
       │                                                       │
┌──────▼──────────────────────────┐             ┌──────────────▼─────────────────────────────────┐
│     DB & Resource Setup         │             │              DB & Storage Setup                │
│                                 │             │                                                │
│  • STATE_DB connect             │             │  • STATE_DB connect                            │
│  • CONFIG_DB connect            │             │  • Create STORAGE_INFO Table                   │
│  • _load_configuration()        │             │  • StorageDevices() — discover block devices   │
│  • _discover_cpu_cores()        │             │  • _load_fsio_rw_statedb()                     │
│  • _initialize_state_db()       │             │  • _load_fsio_rw_json()                        │
└──────┬──────────────────────────┘             │  • _determine_sot()                            │
       │                                        └─────────────┬──────────────────────────────────┘
       │                                                      │
       │                                         ┌────────────▼────────────────────────────┐
       │                                         │          _determine_sot()               │
       │                                         │                                         │
       │                                         │  statedb loaded? ──Yes──► use_statedb   │
       │                                         │       │                    _baseline    │
       │                                         │       No                                │
       │                                         │       │                                 │
       │                                         │  json loaded? ───Yes──► use_json        │
       │                                         │       │                   _baseline     │
       │                                         │       No                                │
       │                                         │       │                                 │
       │                                         │  Neither ────────────► INIT state       │
       │                                         │                         (baseline=0)    │
       │                                         └────────────┬────────────────────────────┘
       │                                                      │
       │                                         ┌────────────▼────────────────────────────┐
       │                                         │  get_static_fields_update_state_db()    │
       │                                         │                                         │
       │                                         │  For each storage_device:               │
       │                                         │    • get_model()                        │
       │                                         │    • get_serial()                       │
       │                                         │    • update STORAGE_INFO|<dev> StateDB  │
       │                                         └────────────┬────────────────────────────┘
       │                                                      │
       │                                                      │
┌──────▼──────────────────────────────────────────────────────▼──────────────────────────────────┐
│                              run() — Spawned Threads / Main Loop                               │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                │
│   platformmond (4 threads)                          STORMOND (single-threaded loop)            │
│   ─────────────────────                          ───────────────────────────────               │
│                                                                                                │
│  ┌──────────────┬──────────────┬─────────────┐  ┌──────────────────────────────────────────┐   │
│  │cpu_snapshot  │ cpu_history  │ ram_snapshot│  │  1. get_configdb_intervals()             │   │
│  │(every 5s)    │ (every Nmin) │ (every 5s)  │  │     • daemon_polling_interval(def 3600s) │   │
│  │              │              │             │  │     • fsstats_sync_interval  (def 86400s)│   │
│  │              │              │ ram_history │  └──────────────────┬───────────────────────┘   │
│  │              │              │ (every Nmin)│                     │                           │
│  └──────┬───────┴────────┬─────┴──────┬──────┘  ┌──────────────────▼──────────────────────┐    │
│         │                │            │         │  2. get_dynamic_fields_update_state_db()│    │
│  ┌──────▼──────┐         │     ┌──────▼──────┐  │                                         │    │
│  │update_      │         │     │update_      │  │  For each storage_device:               │    │
│  │snapshot     │         │     │snapshot     │  │    • fetch_parse_info(blkdevice)        │    │
│  │/proc/stat   │         │     │/proc/meminfo│  │    • get_firmware()                     │    │
│  └──────┬──────┘         │     └────────┬────┘  │    • get_health()                       │    │
│         │                │              │       │    • get_temperature()                  │    │
│    ┌────▼────┐           │        ┌─────▼────┐  │    • get_fs_io_reads/writes()           │    │
│    │Success? │           │        │Success?  │  │    • get_disk_io_reads/writes()         │    │
│    └────┬────┘           │        └────┬─────┘  │    • get_reserved_blocks()              │    │
│    No   │ Yes            │        No   │ Yes    │    • _reconcile_fsio_rw_values()        │    │
│    │    │                │        │    │        │    • update STORAGE_INFO|<dev> StateDB  │    │
│    ▼    │                │        ▼    │        └──────────────────┬──────────────────────┘    │
│  log_err│                │      log_err│                           │                           │
│  skip   │                │      skip   │        ┌──────────────────▼──────────────────────┐    │
│  cycle  │                │      cycle  │        │   _reconcile_fsio_rw_values()           │    │
│         │                │             │        │                                         │    │
│  ┌──────▼──────┐         │   ┌─────────▼─────┐  │  INIT state?                            │    │
│  │_update_cpu_ │         │   │_update_ram_   │  │  total = latest (baseline=0)            │    │
│  │snapshot_db()│         │   │snapshot_db()  │  │                                         │    │
│  └──────┬──────┘         │   └────────┬──────┘  │  JSON baseline?                         │    │
│         │                │            │         │  total = json_total + latest            │    │
│  ┌──────▼──────┐         │   ┌────────▼──────┐  │                                         │    │
│  │_check_      │         │   │_check_        │  │  StateDB baseline? (daemon crash)       │    │
│  │alarm()      │         │   │alarm()        │  │  delta  = latest - statedb_latest       │    │
│  │per core     │         │   │RAM global     │  │  total  = statedb_total + delta         │    │
│  └──────┬──────┘         │   └────────┬──────┘  └─────────────────────────────────────────┘    │
│         │                │            │                             │                          │
│  ┌──────▼──────┐         │   ┌────────▼──────┐   ┌──────────────────▼──────────────────────┐   │
│  │_check_      │         │   │_check_        │   │  stop_event.wait(timeout)               │   │
│  │config_      │         │   │config_        │   │  (polling_interval seconds)             │   │
│  │changes()    │         │   │changes()      │   └──────────┬──────────────┬───────────────┘   │
│  └──────┬──────┘         │   └────────┬──────┘              │              │                   │
│         │                │            │                  SIGTERM/      timeout                 │
│  ┌──────▼──────┐         │   ┌────────▼──────┐          SIGINT         elapsed                 │
│  │stop_event.  │         │   │stop_event.    │              │              │                   │
│  │wait(5s)     │         │   │wait(5s)       │              │   ┌──────────▼─────────────────┐ │
│  └──────┬──────┘         │   └────────┬──────┘              │   │elapsed > fsstats_sync_     │ │
│         │                │            │                     │   │interval?                   │ │
│         └────────────────┼────────────┘                     │   └──────┬──────────┬──────────┘ │
│                          │                                  │         Yes         No           │
│                          │                                  │          │          │            │
│                          │                                  │   ┌──────▼──────┐   │            │
│                          │                                  │   │sync_fsio_   │   │            │
│                          │                                  │   │rw_json()    │   │            │
│                          │                                  │   │STATE_DB ──► │   │            │
│                          │                                  │   │JSON file    │   │            │
│                          │                                  │   └──────┬──────┘   │            │
│                          │                                  │      OK? │ No       │            │
│                          │                                  │     Yes  ▼          │            │
│                          │                                  │      │  log_warning │            │
│                          │                                  │      ▼              │            │
│                          │                                  │  write_sync_time_   │            │
│                          │                                  │  statedb()          │            │
│                          │                                  │      │              │            │
│                          │                                  │      └──────┬───────┘            │
│                          │                                  │             │                    │
│                          │                                  │         loop again ◄─────────────┘
└──────────────────────────┼──────────────────────────────────┼──────────────────────────────────┘
                           │                                  │
                           │                                  │
          ┌────────────────▼──────────────────────────────────▼──────────────────┐
          │                    SIGTERM / SIGINT received                         │
          ├────────────────────────────────┬─────────────────────────────────────┤
          │         platformmond           │              STORMOND               │
          │                                │                                     │
          │  signal_handler()              │  signal_handler()                   │
          │  • raises KeyboardInterrupt    │  • sync_fsio_rw_json()              │
          │                                │    (STATE_DB → JSON file)           │
          │  deinit()                      │  • write_sync_time_statedb()        │
          │  • stop_event.set()            │  • exit_code = 128 + sig            │
          │  • join threads (timeout=10s)  │  • stop_event.set()                 │
          └────────────────────────────────┴─────────────────────────────────────┘
                           │                                   │
          ┌────────────────▼───────────────────────────────────▼──────────────────┐
          │                    main() exits / sys.exit(exit_code)                 │
          │                    supervisord restarts if needed                     │
          └───────────────────────────────────────────────────────────────────────┘

#### 8.6 Serviceability and Debug

##### 8.6.1 Logging

All daemon operations are logged via Python `syslog` module with facility `LOG_USER`.

###### 8.6.1.1 platformmond Logging

| Log Level     | Usage                                                                   |
|---------------|-------------------------------------------------------------------------|
| `LOG_ERR`     | /proc/stat or /proc/meminfo read failure; STATE_DB write failure; invalid CONFIG_DB values                |
| `LOG_WARNING` | CPU/RAM alarm raised (structured); CPU/RAM alarm cleared (human readable)                                 |
| `LOG_INFO`    | CPU/RAM alarm cleared (structured); daemon start/stop; history buffer reset; configuration change applied |
| `LOG_ALERT`   | CPU/RAM alarm raised (human readable)                                                                     |

```bash
# View live platformmond logs
sudo tail -f /var/log/syslog | grep platformmond

# Filter by alarm events only
sudo grep -iE 'alarm|raised|cleared|threshold' /var/log/syslog | grep platformmond

###### 8.6.1.2 stormond Logging

| Log Level     | Usage                                                                   |
|---------------|-------------------------------------------------------------------------|
| `LOG_ERR`     | Partition read failure; STATE_DB write failure                          |
| `LOG_WARNING` |Threshold alarm raised; platform API failure; partition read failure     |                         |
| `LOG_INFO`    |Daemon start/stop; history buffer reset; partition discovery             |

# View stormond logs in syslog
sudo grep stormond /var/log/syslog

# View logs in real-time
sudo tail -f /var/log/syslog | grep stormond
```

##### 8.6.2 Techsupport Integration

The `show techsupport` command shall be extended to collect:

| Artifact          | Source                                                               |
|-------------------|----------------------------------------------------------------------|
| Daemon log        | `sudo tail -f /var/log/syslog | grep -iE 'platformmond|stormond'`       |
| CONFIG_DB tables  | `CPU_GLOBAL`, `RAM_GLOBAL`, `STORAGE_GLOBAL`                         |
| STATE_DB tables   | `CPU_TABLE`, `CPU_HISTORY_TABLE`, `RAM_HISTORY_TABLE`,`STORAGE_TABLE`|
| System files      | `/proc/stat`, `/proc/meminfo`, `/proc/mounts`, `df -h` output        |

### 9. Warmboot and Fastboot Design Impact

#### 9.1 Warm Boot Requirements

- Configuration (CPU/RAM thresholds via CPU_GLOBAL, RAM_GLOBAL; storage thresholds via STORAGE_GLOBAL) shall be retained across warm boot via CONFIG_DB persistence
- Runtime state data (CPU_TABLE, CPU_HISTORY_TABLE, RAM_TABLE, RAM_HISTORY_TABLE, STORAGE_TABLE, and active alarms) will be lost and re-collected after restart
- No special warmboot logic is required — platformmond and stormond operates in platform monitoring plane only

#### 9.2 Warm Boot Support

The daemon is **not warmboot-aware** and does not require special handling during warm or fast boot scenarios.

### 10. Restrictions/Limitations

1. **History Data Persistence**
   - History data is stored in STATE_DB (volatile memory)
   - History is lost on system restart, warmboot, or fastboot
   - No persistent storage of historical metrics

2. **CPU Monitoring Scope**
   - Per-logical-core CPU utilization is collected and reported in STATE_DB
   - Aggregate CPU utilization is computed internally for threshold comparison only
   - Per-container CPU utilization is not supported
   - Per-socket CPU utilization for multi-socket systems is not supported

3. **Storage Monitoring Scope**
   - Only permanently attached devices monitored (/dev/sd*, /dev/nvme*, /dev/mmcblk*, /dev/vd*, /dev/xvd*, /dev/hd*)
   - Removable storage excluded (/sys/block/<dev>/removable == 1)
   - Only mounted partitions reported (requires entry in /proc/mounts)
   - Pseudo-filesystems excluded (tmpfs, devtmpfs, squashfs, overlay, iso9660)
   - No aggregate device-level utilization (per-partition only)
   - No historical utilization data (point-in-time snapshots only)

4. **Threshold Monitoring**
   - Only maximum thresholds are supported (CPU, memory, disk)
   - Minimum thresholds are not supported
   - Per-core CPU thresholds are not supported (only aggregate)
   - Per-partition disk thresholds are not supported
   - Single threshold applies to all partitions (no per-partition configuration)
   - No threshold hysteresis or alarm rate limiting

5. **Alarm Notification**
   - Syslog is the only notification mechanism
   - SNMP traps and other notification methods are out of scope
   - No alarm rate limiting or suppression
   - Syslog-only notifications (no SNMP traps, email, webhooks)
   - Alarms auto-clear when condition resolves (no manual acknowledgment)

6. **History Configuration**
   - History interval must be less than history duration
   - Maximum history duration is 180 minutes (24 hours)
   - Maximum history interval is 10 minutes
   - Changing history configuration clears existing history data

7. **Performance Considerations**
   - Metric collection uses system resources (CPU, I/O)
   - Very short history intervals may impact system performance
   - Recommended minimum history interval is 5 minutes
   - Single-threaded execution (no parallel partition scanning)
   - os.statvfs() has no timeout (may hang on stale NFS mounts)
   - Utilization rounded to 2 decimal places

### 11. Testing Requirements/Design

#### 11.1 Unit Test Cases

All functional test cases were executed manually on the target system to validate the monitoring behavior in real-world conditions.

| Test ID  | Test Case Description                         | Requirement |
|----------|-----------------------------------------------|-------------|
| FT-01    | CPU snapshot retrieval                        | FR-1        |
| FT-02    | CPU history with default config               | FR-2        |
| FT-03    | CPU history with custom config                | FR-2        |
| FT-04    | CPU threshold alarm — raise                   | FR-6        |
| FT-05    | CPU threshold alarm — clear                   | FR-6        |
| FT-06    | Syslog verification — alarm raised            | FR-9        |
| FT-07    | Syslog verification — alarm cleared           | FR-9        |
| FT-08    | Default threshold values                      | FR-6,FR-7,  |
|          |                                               | FR-8        |
| FT-09    | History not persisted across reboot           | FR-2        |
| FT-10    | Config persisted across reboot                | FR-6        |
| FT-11    | Show config command                           | FR-2, FR-6  |
| FT-12    | Daemon restart recovery                       | FR-1        |
| FT-13    | RAM snapshot retrieval                        | FR-3        |
| FT-14    | RAM snapshot accuracy                         | FR-3        |
| FT-15    | RAM history with default config               | FR-4        |
| FT-16    | RAM history with custom config                | FR-4        |
| FT-17    | RAM history circular buffer                   | FR-4        |
| FT-18    | RAM history enable at runtime                 | FR-4        |
| FT-19    | RAM history disable at runtime                | FR-4        |
| FT-20    | RAM threshold alarm — raise                   | FR-7        |
| FT-21    | RAM threshold alarm — clear                   | FR-7        |
| FT-22    | RAM alarm no duplicate raise                  | FR-7, FR-9  |
| FT-23    | RAM alarm no duplicate clear                  | FR-7, FR-9  |
| FT-24    | Syslog verification — RAM alarm raised        | FR-9        |
| FT-25    | Syslog verification — RAM alarm cleared       | FR-9        |
| FT-26    | Default RAM threshold                         | FR-7        |
| FT-27    | RAM config persisted across reboot            | FR-7        |
| FT-28    | RAM history not persisted across reboot       | FR-4        |
| FT-29    | RAM interval/duration change while history    | FR-4        |
|          | disabled                                      |             |
| FT-30    | RAM interval/duration change while history    | FR-4        |
|          | enabled                                       |             |
| FT-31    | Daemon restart — RAM recovery                 | FR-3        |
| FT-32    | RAM STATE_DB entry manually deleted           | FR-3        |
| FT-33    | Storage utilization accuracy                  | FR-5        |
| FT-34    | Storage threshold alarm                       | FR-8        |


#### 11.2 System Test Cases

Test Summary Table

| Test ID | Test Case Description                         | Requirement                |
|---------|-----------------------------------------------|----------------------------|
| TC-1.1  | Current CPU utilization per core              | RF-01                      | 
| TC-1.2  | CPU threshold NA when not configured          | RF-01, RF-06               | 
| TC-1.3  | CPU threshold NA when set to 0                | RF-06                      | 
| TC-1.4  | CPU utilization under load                    | RF-01                      | 
| TC-2.1  | CPU history default status disabled           | RF-02                      | 
| TC-2.2  | CPU history enable and verify                 | RF-02                      | 
| TC-2.3  | CPU history disable and verify                | RF-02                      | 
| TC-2.4  | CPU history interval config when disabled     | RF-02                      | 
| TC-2.5  | CPU history duration config when disabled     | RF-02                      | 
| TC-2.6  | CPU history config rejected when enabled      | RF-02                      | 
| TC-2.7  | CPU history default duration and interval     | RF-02                      | 
| TC-2.8  | CPU history data collection and display       | RF-02                      | 
| TC-2.9  | CPU history show when disabled, no data       | RF-02                      | 
| TC-2.10 | CPU history show when disabled, data in Redis | RF-02                      | 
| TC-2.11 | CPU history not retained across reboot        | RF-02                      | 
| TC-2.12 | CPU history invalid interval rejected         | RF-02                      | 
| TC-2.13 | CPU history invalid duration rejected         | RF-02                      | 
| TC-2.14 | CPU history FIFO buffer behavior              | RF-02                      | 
| TC-3.1  | Current RAM utilization retrieval             | RF-03                      | 
| TC-3.2  | RAM threshold NA when not configured          | RF-03, RF-07               | 
| TC-3.3  | RAM utilization under load                    | RF-03                      | 
| TC-4.1  | RAM history default status disabled           | RF-04                      | 
| TC-4.2  | RAM history enable and collect data           | RF-04                      | 
| TC-4.3  | RAM history config rejected when enabled      | RF-04                      | 
| TC-4.4  | RAM history default duration and interval     | RF-04                      | 
| TC-4.5  | RAM history show when disabled, no data       | RF-04                      | 
| TC-4.6  | RAM history show when disabled, data in Redis | RF-04                      | 
| TC-4.7  | RAM history not retained across reboot        | RF-04                      | 
| TC-4.8  | RAM history invalid range rejected            | RF-04                      | 
| TC-4.9  | RAM history independent from CPU history      | RF-04                      | 
| TC-5.1  | Storage partition info and utilization        | RF-05                      | 
| TC-5.2  | Only mounted partitions reported              | RF-05                      | 
| TC-5.3  | Storage utilization changes reflected         | RF-05                      | 
| TC-5.4  | Storage threshold NA when not configured      | RF-05, RF-08               | 
| TC-6.1  | CPU threshold configure valid value           | RF-06                      | 
| TC-6.2  | CPU threshold default 85%                     | RF-06                      | 
| TC-6.3  | CPU alarm generated on threshold breach       | RF-06                      | 
| TC-6.4  | CPU alarm auto-cleared                        | RF-06                      | 
| TC-6.5  | CPU threshold invalid range rejected          | RF-06                      | 
| TC-6.6  | CPU threshold 0 shows NA                      | RF-06                      | 
| TC-7.1  | RAM threshold configure valid value           | RF-07                      | 
| TC-7.2  | RAM threshold default 80%                     | RF-07                      | 
| TC-7.3  | RAM alarm generated on threshold breach       | RF-07                      | 
| TC-7.4  | RAM alarm auto-cleared                        | RF-07                      | 
| TC-7.5  | RAM threshold invalid range rejected          | RF-07                      | 
| TC-7.6  | RAM threshold 0 shows NA                      | RF-07                      | 
| TC-8.1  | Storage threshold configure valid value       | RF-08                      | 
| TC-8.2  | Storage threshold default 75%                 | RF-08                      | 
| TC-8.3  | Storage alarm generated on threshold breach   | RF-08                      | 
| TC-8.4  | Storage alarm auto-cleared                    | RF-08                      | 
| TC-8.5  | Storage threshold invalid range rejected      | RF-08                      | 
| TC-8.6  | Storage threshold 0 shows NA                  | RF-08                      | 
| TC-9.1  | Syslog CPU threshold violation logged         | RF-09                      | 
| TC-9.2  | Syslog CPU alarm cleared logged               | RF-09                      | 
| TC-9.3  | Syslog RAM threshold violation logged         | RF-09                      | 
| TC-9.4  | Syslog RAM alarm cleared logged               | RF-09                      | 
| TC-9.5  | Syslog storage threshold violation logged     | RF-09                      | 
| TC-9.6  | Syslog storage alarm cleared logged           | RF-09                      | 
| TC-10.1 | Config DB missing entries show N/A            | RF-01, RF-03, RF-05        | 
| TC-10.2 | Boundary values accepted                      | RF-06, RF-07, RF-08        | 
| TC-10.3 | Concurrent alarms multiple resources          | RF-06, RF-07, RF-08, RF-09 | 

## Appendix A: Default Configuration Summary

| Parameter                 | Default Value |
|---------------------------|---------------|
| CPU History Duration      | 60 minutes    |
| CPU History Interval      | 5 minutes     |
| Ram History Duration      | 60 minutes    |
| Ram History Interval      | 5 minutes     |
| CPU Max Threshold         | 85%           |
| Ram Utilization Threshold | 80%           |
| Storage Max Threshold     | 75%           |

## Appendix B: init_cfg.json Defaults

These defaults are loaded via `init_cfg.json` during first boot or when no configuration exists:

```json:files/image_config/init_cfg/init_cfg.json.fragment
{
    "CPU_GLOBAL": {
        "global": {
            "cpu_history_measurement_interval": "5",
            "cpu_history_duration": "60",
            "history_status": "disabled",
            "cpu_utilization_threshold": "85"
        }
    },
    "RAM_GLOBAL": {
        "global": {
            "ram_history_measurement_interval": "5",
            "ram_history_duration": "60",
            "history_status": "disabled",
            "ram_utilization_threshold": "80"
        }
    }
    "STORAGE_GLOBAL": {
        "global": {
            "storage_utilization_threshold: "75"
        }
    }             
}
```

## Appendix C: Syslog Message Reference

| Event                 | Severity      | Message Format|
|-----------------------|---------------|---------------|
| CPU alarm raised      | `LOG_WARNING` | `pmon#platformmond[{pid}]: PLATFORM_ALARM: type=CPU_UTILIZATION, resource={cpu_index}|{core_index}, action=raised, current={value}, threshold={threshold}` |
| CPU alarm cleared     | `LOG_INFO`    | `pmon#platformmond[{pid}]: PLATFORM_ALARM: type=CPU_UTILIZATION, resource={cpu_index}|{core_index}, action=cleared, current={value}, threshold={threshold}` | |
| RAM alarm raised      | `LOG_WARNING` | `pmon#platformmond[{pid}]: PLATFORM_ALARM: type=RAM_UTILIZATION, resource=None, action=raised, current={value}, threshold={threshold}` |
| RAM alarm cleared     | `LOG_INFO`    | `pmon#platformmond[{pid}]: PLATFORM_ALARM: type=RAM_UTILIZATION, resource=None, action=cleared, current={value}, threshold={threshold}`|
| Storage alarm raised  | `LOG_WARNING` | pmon#stormond[{pid}]: STORAGE ALARM ACTIVE: {device}|{partition} utilization at {value}% exceeds threshold {threshold}%|
| Storage alarm cleared | `LOG_INFO`    | pmon#stormond[{pid}]: STORAGE ALARM CLEARED: {device}|{partition} utilization at {value}% is below threshold {threshold}% |


## Appendix D: Requirements Traceability Matrix

| Requirement             | Design Section | DB Tables                         | CLI Commands                  | Test Cases          |
|-------------------------|----------------|-----------------------------------|-------------------------------|---------------------|
| FR-1 (CPU current)      | 2.2.1, 3.3.2   | STATE_DB: `CPU_TABLE`             | `show platform cpu`           | UT-01–04, FT-01     |
| FR-2 (CPU history)      | 2.2.1, 3.3.2   | STATE_DB: `CPU_HISTORY_TABLE`     | `show platform cpu-history`, `sudo config platform cpu-history status enable` | UT-07–09, FT-02–03, FT-21, FT-27 |
| FR-3 (Memory current)   | 2.2.2, 3.3.2   | STATE_DB: `RAM_GLOBAL`            | `show platform ram`           | UT-05–06, FT-04     |
| FR-4 (Memory history)   | 2.2.2, 3.3.2   | STATE_DB: `RAM_HISTORY_TABLE`     | `show platform ram-history` , `config platform ram-history status enable ` , `config platform ram-history duration <value> ` , `config platform ram-history interval <value> `| UT-07–09, FT-05, FT-21 |
| FR-5 (Storage)          | 2.2.3, 3.3.2   | STATE_DB: STORAGE_TABLE           | `show platform storage`       | UT-10–13, FT-06–07  |
| FR-6 (CPU threshold)    | 2.2.6, 3.3.3   | CONFIG_DB: `CPU_GLOBAL`, STATE_DB: `CPU_TABLE` | `sudo config platform cpu utilization-threshold <0-100>`, `show platform cpu` | UT-17–20, FT-14–15, FT-20 |
| FR-7 (Memory threshold) | 2.2.6, 3.3.3   | CONFIG_DB: `RAM_GLOBAL`           | `config platform ram utilization-threshold <value>`, `show platform ram` | UT-17–20, FT-16, FT-20 |
| FR-8 (Storage threshold)| 2.2.6, 3.3.3   | CONFIG_DB: STORAGE_GLOBAL|globals | config platform storage utilization-threshold <0-100>  show platform storage | UT-21–22, FT-17, FT-20 |
| FR-9 (Syslog)           | 2.2.7, 3.3.3   | N/A (syslog output)               | N/A (verify via `journalctl`) | UT-30–31, FT-18–19  |
