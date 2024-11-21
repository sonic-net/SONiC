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

Additionally, there are also various files created and deleted in the /tmp directory which contribute towards disk writes by the kernel journal.

## Optimizations
The following optimizations are proposed to reduce disk writes:

- **jbd2**: Evaluate disabling kernel journaling if benefits outweigh trade-offs.
- **/tmp**: Relocate the /tmp directory to tmpfs filesystem
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
Below are the disk writes in MiB per day after implementing the optimizations proposed above:

| HWSKU | OS Version | Unoptimized | Optimization A | Optimization B | Optimization C |
|-------|------------|-------------|----------------|----------------|----------------|
| SKU1  | Version_1  | 872.89      | 66             | 135.9          | 147.4          |
|       | Version_2  | 667.81      | 81             | 55.8           | 273.3          |
|       | Version_3  | 719.52      | 70.4           | 87.5           | 133.2          |
| SKU2  | Version_1  | 627.81      | 62.9           | 23.5           | 99.1           |
|       | Version_3  | 729.14      | 77             | 8              | 43.3           |
| SKU3  | Version_1  | 762.63      | 50             | 175.3          | 237.3          |
|       | Version_2  | 591.26      | 52             | 94.4           | N/A            |
|       | Version_3  | 643.14      | 59             | 206            | 96             |

##### **Table 4**

Where:
Optimization A: All optimizations mentioned in the previous section, including disabling journaling
Optimization B: User space modifications, journaling is enabled and **/tmp is mounted to tmpfs**
Optimization C: User space modifications, journaling is enabled and **/tmp is mounted to disk**


### Key Takeaways from Disk Write Comparisons Across Scenarios

1. **Unoptimized Scenario:**
   - The baseline disk write volumes are significantly higher across all hardware SKUs and OS versions, with values exceeding **600 MiB/day** in most cases.
   - This reflects the default behavior of the system with no mitigations applied, highlighting the impact of verbose write patterns in SONiC.

2. **Optimization A (User Space + Journaling Disabled):**
   - Shows the **greatest reduction in disk writes**, with values often below **100 MiB/day**.
   - Journaling contributes heavily to disk writes in the unoptimized state, and disabling it leads to a dramatic reduction.
   - **Trade-offs**: Risk of data corruption, longer recovery times, and filesystem inconsistency must be carefully considered before adopting this approach.

3. **Optimization B (All User Space Optimizations):**
   - Achieves significant write reductions compared to the unoptimized state, especially in processes like `/tmp` handling, log relocation, and reduced writes from vtysh and worker threads.
   - Write reductions are generally moderate, with values staying between **50-200 MiB/day**, depending on the SKU and OS version.
   - **Advantage**: Maintains data integrity by keeping journaling enabled.

4. **Optimization C (All User Space Optimizations Except `/tmp` on Disk):**
   - Results in higher disk writes compared to Optimization B, especially when `/tmp` remains on disk.
   - Write volumes exceed **200 MiB/day** in some cases, suggesting `/tmp` contributes a substantial portion of unnecessary disk writes in the default configuration.

5. **Relative Importance of `/tmp` Relocation:**
   - The comparison between Optimizations B and C highlights the critical role of relocating `/tmp` to tmpfs. 
   - Relocating `/tmp` alone contributes significantly to write reduction, emphasizing the priority of this optimization.

6. **SKU and OS Version Variability:**
   - Disk writes and the impact of optimizations vary by SKU and OS version, with SKU3 generally showing higher disk writes in the unoptimized state.
   - This variability underscores the importance of tailoring optimizations to specific hardware and OS configurations.

7. **Overall Effectiveness of User Space Optimizations:**
   - Even without disabling journaling (Optimization B), user space changes like log relocation, command streamlining, and `/tmp` adjustments substantially mitigate disk writes.
   - This suggests a strong case for prioritizing these optimizations as a low-risk, high-impact approach.
