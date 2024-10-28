# Analysis of Disk Writers in SONiC Devices

## Context
Numerous devices are transitioning into a read-only file system state due to excessive disk writes in the verbose SONiC OS. Combined with the inability to perform regular power cycles on the switches, this leads to accelerated storage degradation.

## Objective
This analysis aims to identify the largest disk writers on three vendor devices (referred to as SKU1, SKU2, and SKU3) running SONiC OS versions Version_1, Version_2, and Version_3, and to develop optimization recommendations to reduce disk writes.

## Methodology
The following methodology was employed:

- **Devices Queried**: 100 devices each of SKU1, SKU2, and SKU3 across Version_1, Version_2, and Version_3 OS versions (900 devices total).
- **Geographic Spread**: Devices were distributed across different data centers.
- **Tools Used**:
  - **blktrace** and **blkparse**: Provided detailed insights into I/O operations at the block layer, ideal for analyzing disk I/O patterns.
  - Blktrace data was saved to `/dev/shm` (tmpfs) to avoid interference during data collection.

### Data Written (MiB/day) for All HWSKUs Across All OS Versions

| HWSKU   | OS Version  | Max   | Min   | Mean  |
|---------|-------------|-------|-------|-------|
| SKU1    | [Version_1](images/sku1_imgV1.png) | 1158.00 | 587.78 | 872.89 |
|         | [Version_2](images/sku1_imgV2.png) | 748.39  | 587.24 | 667.81 |
|         | [Version_3](images/sku1_imgV3.png) | 723.08  | 715.96 | 719.52 |
| SKU2    | [Version_1](images/sku2_imgV1.png) | 775.06  | 566.12 | 627.81 |
|         | [Version_2](images/sku2_imgV2.png) | 734.31  | 696.37 | 714.76 |
|         | [Version_3](images/sku2_imgV3.png) | 768.36  | 685.77 | 729.14 |
| SKU3    | [Version_1](images/sku3_imgV1.png) | 997.90  | 527.36 | 762.63 |
|         | [Version_2](images/sku3_imgV2.png) | 676.11  | 506.42 | 591.26 |
|         | [Version_3](images/sku3_imgV3.png) | 740.78  | 545.50 | 643.14 |
##### **Table 1**


## Results
The following table summarizes the primary disk writers averaged across 100 devices per HWSKU and OS version:

| Process            | Description                       | Disk Writes (% of Total) |
|--------------------|-----------------------------------|--------------------------|
| **jbd2**           | Kernel journaling thread         | 60%                      |
| **vtysh**          | CLI for network protocols        | 20%                      |
| **kworker/u8:x**   | Worker threads                   | 15%                      |
| **monit**          | Monitoring utility               | 3%                       |
| **logrotate, bash**| Linux utilities/shell            | 2%                       |

**Table 2**

- **jbd2**: Kernel journaling.
- **vtysh**: "show bgp summary json" repeatedly written to `~/.history_frr` within BGP container due to bgpmon command repetition.
- **kworker/u8:x**: Includes multiple workers, most common being:
  - `swss:supervisor-proc-exit-listener` writing logs to `/var/log/supervisor/` in the swss container.
  - OverlayFS inodes writing extended attributes.
- **monit**: Updates state file in `/var/lib/monit/`.
- **logrotate**: Updates status file in `/var/lib/logrotate/`.

## Optimizations
The following optimizations are proposed to reduce disk writes:

- **jbd2**: Evaluate disabling kernel journaling if benefits outweigh trade-offs.
- **vtysh**: Modify command in `bgpmon/bgpmon.py` (Line 79) to:
  ```python
  cmd = "vtysh -H /dev/null -c 'show bgp summary json'"

- **kworker/u8:x**: For `supervisor-proc-exit-listener`, relocate log files to tmpfs: `/dev/shm/supervisor/` within swss container.
- **monit and logrotate**: Move state and status files to tmpfs: `/dev/shm/monit`, `/dev/shm/logrotate`.

### A Note on disabling Kernel Journaling

Disabling journaling on an EXT4 filesystem offers a few tangible benefits, but they come with significant trade-offs, especially in terms of data integrity and stability. Below are the pros and cons of disabling journaling.

#### **Advantages of Disabling Journaling**

1. **Reduced Write Overhead**: Disabling journaling reduces write overhead, as the system doesn’t need to log changes twice (once in the journal, then in the actual data). This could improve write performance, especially for I/O-intensive applications.

2. **Extended SSD Lifespan:**: Write operations are costly in terms of lifespan because SSDs have a limited number of write cycles. Disabling journaling could help extend the lifespan of the SSD by reducing the number of write operations, particularly in write-heavy workloads.


#### **Consequences of Disabling Journaling**

1. **Increased Risk of Data Corruption**: Without journaling, the system cannot track incomplete or interrupted operations, making the filesystem more vulnerable to corruption in the event of a crash, power failure, or forced reboot. Data in-flight could be lost or corrupted as there is no journal to roll back to a known good state.

2. **Longer Recovery Times**: When journaling is disabled, recovery after a crash or unclean shutdown will take much longer since `fsck` will need to be performed, which is time-consuming on large volumes. Journaling significantly speeds up recovery times by replaying only the necessary changes.

3. **Loss of Filesystem Consistency**: Journaling helps maintain metadata consistency (e.g., file ownership, permissions etc.). Without it, metadata inconsistencies could result in file or directory errors, making files inaccessible or corrupted.



### Results with Optimizations
Below are the disk writes per day after implementing the optimizations proposed above:

| HWSKU   | OS Version  | MiB/day |
|---------|-------------|---------|
| SKU1    | Version_1   | 66      |
|         | Version_2   | 81      |
|         | Version_3   | 70.4    |
| SKU2    | Version_1   | 62.9    |
|         | Version_3   | 77      |
| SKU3    | Version_1   | 50      |
|         | Version_2   | 52      |
|         | Version_3   | 59      |
##### **Table 4**

### Takeaways

1. **Optimizations Lead to Significant Disk Write Reductions**:
   - The implemented optimizations resulted in substantial reductions in disk writes across all Vendor HWSKUs and OS versions. For example, **Vendor SKU1 running image Version_3** experienced a drop from **719.52 MiB/day** to **70.4 MiB/day**, a **90.2%** reduction, showing that moving logs and state files to tmpfs and disabling journaling had a profound effect on reducing disk writes.

2. **Journaling and Process-Level Optimizations Were Key**:
   - The largest reductions were due to the optimizations of the **jbd2** kernel journaling process, which accounted for **60%** of the original disk writes.

   - The modifications to **vtysh** also had a major impact. The transition to a more efficient command structure stopped **vtysh** from writing **20%** of the total data, completely eliminating its disk usage in optimized environments.

3. **Benefits were Platform-Agnostic**:
   - All platforms benefited from the optimizations, with consistent results observed in **SKU1**, **SKU2**, and **SKU3**. For example:
     - **SKU1 running image Version_3**: Disk writes reduced from **719.52 MiB/day** to **70 MiB/day** (a **90.3%** reduction).
     - **SKU3 running image Version_2**: Disk writes reduced from **591.26 MiB/day** to **52 MiB/day** (a **91.2%** reduction).
     - **SKU2 running image Version_1**: Disk writes reduced from **627.81 MiB/day** to **62.9 MiB/day** (a **90%** reduction).

   - This indicates that the optimizations are broadly applicable across different hardware platforms and OS versions.

4. **Reduction in Disk Wear and System Longevity**:
   - The significant drop in disk writes directly translates into reduced wear and tear on storage devices, which improves the overall reliability and lifespan of the hardware. This reduction is critical in production environments where devices often cannot be power-cycled frequently. 
