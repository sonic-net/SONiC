# ZMQ Optimizations for DASH

## High Level Design Document
### Rev 0.1

# Table of Contents

- [Revision](#revision)
- [About this Manual](#about-this-manual)
- [Definitions/Abbreviation](#definitionsabbreviation)
- [1 Overview](#1-overview)
  * [1.1 Introduction and Scope](#11-introduction-and-scope)
  * [1.2 Benefits of this Feature](#12-benefits-of-this-feature)
- [2 Requirements](#2-requirements)
  * [2.1 Functional Requirements](#21-functional-requirements)
  * [2.2 Testing Requirements](#22-testing-requirements)
- [3 Syncd Changes](#3-syncd-changes)
  * [3.1 Syncd Flow (Before)](#31-syncd-flow-before)
  * [3.2 Syncd Flow (After)](#32-syncd-flow-after)
  * [3.3 Memory Footprint Comparison](#33-memory-footprint-comparison)
  * [3.4 ENI Configuration Time](#34-eni-configuration-time)
  * [3.5 Configuration](#35-configuration)
- [4 Design](#4-design)
  * [4.1 Remove Syncd Redis Objects with ZMQ](#41-remove-syncd-redis-objects-with-zmq)
  * [4.2 ZMQ Buffer Size Optimization](#42-zmq-buffer-size-optimization)
  * [4.3 Increase Hugepages for DPU](#43-increase-hugepages-for-dpu)
  * [4.4 Bulker and Pop Batch Size Optimization](#44-bulker-and-pop-batch-size-optimization)
- [5 Testing](#5-testing)
- [6 Future Work](#6-future-work)
- [7 References](#7-references)

# Revision

| Rev  |    Date    |            Author            | Change Description |
|:----:|:----------:|:----------------------------:|:-------------------|
| 0.1  | 01/15/2026 | Connor Roos, Vivek Reddy Karri | Initial version    |

# About this Manual

This document describes the optimization to reduce ASIC DB memory footprint by using zmq to process object operations in SONiC.

# Definitions/Abbreviation

| Term     | Description                                              |
|----------|----------------------------------------------------------|
| ZMQ      | ZeroMQ - High-performance asynchronous messaging library |
| ASIC DB  | ASIC Database - Redis database storing SAI object state  |
| syncd    | Synchronization daemon for SAI operations                |
| SAI      | Switch Abstraction Interface                             |
| DASH     | Disaggregated APIs for SONiC Hosts                       |
| DPU      | Data Processing Unit                                     |
| ENI      | Elastic Network Interface                                |
| VmRSS    | Virtual Memory Resident Set Size - physical memory used  |
| NASA     | NVIDIA Accelerated Switch and Packet Processing (ASAP2)  |
| CA2PA    | Customer Address to Provider Address mapping             |

# 1 Overview

## 1.1 Introduction and Scope

For almost all production versions of SONiC, syncd manages ASIC objects by reading changes to the ASIC_DB Redis database and applying them over SAI, then writing the result back to ASIC_DB. The one exception to this was the SmartSwitch DPU version of SONiC, which read the changes over ZMQ but also wrote the state and results to ASIC_DB.

This led to significant failures in scale testing:
- **Applying DASH Scale for 32 ENIs** was taking prohibitively long (6-7 hours)
- **64 ENI configuration** led to out-of-memory (OOM) errors and DPU restart
- **Running show techsupport** led to OOM errors and DPU restart
- DPUs have less memory than most switches and could not handle copying the database during diagnostic operations

We decided to optimize by effectively removing the Redis database from DPU SONiC entirely and only using the ZMQ notifications to track ASIC object updates.

## 1.2 Benefits of this Feature

The optimization removes unnecessary Redis objects from syncd to save on memory, which is smaller on DPU SONiC, necessitating this change. These objects are instead ZMQ notifications that are removed from memory after being programmed by SAI, but are recorded in SAI record files. This both reduced memory consumption for ENIs (which exceeded 64 GB for 64 ENIs), and decreased the time spent per operation in syncd as the Redis calls were removed.


# 2 Requirements

## 2.1 Functional Requirements

- When ZMQ notifications are enabled, syncd shall not create Redis notification objects in ASIC DB
- No functionality is lost when this optimization is enabled
- All changes are part of 202511 and master branches

## 2.2 Testing Requirements

Testing for this feature consisted of two tests: a 32 ENI and 64 ENI test to validate the upper limit of DASH objects that can be programmed on the DPU. Each test consists of 1024 VNETs programmed at the start followed by testing how long it took to program ENIs that consisted of these objects each:
- 100,000 outbound routes
- 125,000 outbound CA to PA mappings
- 2 inbound routes

GNMI was applied using a custom GNMI configurator with chunksize set to 10000 entries per chunk sent to orchagent.

# 3 Syncd Changes

## 3.1 Syncd Flow (Before)

Notifications prior to the change were tracked by ZMQ Push/Pull sockets. State in ASIC_DB is updated only after the ASIC is successfully programmed. `sairedis.rec` is also updated with an entry that includes the SAI call and its response code.

## 3.2 Syncd Flow (After)

With the `zmq_sync` notification mode enabled, Redis objects are no longer created or destroyed in ASIC_DB. State is no longer written to ASIC_DB after ASIC programming—instead, the SAI call results are only recorded in `sairedis.rec`. This eliminates the Redis memory overhead while maintaining the ability to track and replay SAI operations.

## 3.3 Memory Footprint Comparison

### Prior to Optimization

| ENI Count | Total Memory | NASA    | Orchagent | Syncd   | ASIC_DB |
|-----------|--------------|---------|-----------|---------|---------|
| 32 ENI    | 55 GB        | 2.7 GB  | 7.4 GB    | 500 MB  | 4.6 GB  |
| 63+ ENI   | > 64 GB*     | > 23 GB | -         | -       | -       |

\* SONiC crashes due to no free memory at 63 ENI

### After Optimization

| ENI Count | Total Memory** | NASA     | Orchagent | Syncd  | ASIC_DB |
|-----------|----------------|----------|-----------|--------|---------|
| 1 ENI     | 32 GB          | 328.3 MB | 600 MB    | 330 MB | 5.5 MB  |
| 16 ENI    | 37 GB          | 1.1 GB   | 3.6 GB    | 325 MB | 5.5 MB  |
| 32 ENI    | 42 GB          | 1.9 GB   | 7.5 GB    | 344 MB | 5.5 MB  |
| 64 ENI    | 49 GB          | 3 GB     | 13 GB     | 350 MB | 5.5 MB  |

\*\* 22.85 GB allocated for hugepages used by NASA

### Key Improvements

**32 ENI Test Results:**

| Parameter                    | Previous Value | New Value |
|------------------------------|----------------|-----------|
| Total Used Memory            | 55 GB          | 42 GB     |
| VmRSS syncd                  | 500 MB         | 344 MB    |
| ASIC_DB Size                 | 4.6 GB         | 5.5 MB    |

**64 ENI Test Results:**

| Parameter                    | Previous Value | New Value |
|------------------------------|----------------|-----------|
| Total Used Memory            | > 64 GB (crash)| 49 GB     |
| VmRSS syncd                  | N/A (crash)    | 350 MB    |

## 3.4 ENI Configuration Time

### 32 ENI Test - Current Results

| Metric                       | Time (seconds) | Details     |
|------------------------------|----------------|-------------|
| Shortest ENI Config          | 52.36 sec      | ENI 1       |
| Longest ENI Config           | 91.24 sec      | ENI 32      |
| Average ENI Config           | 68.18 sec      | -           |

### Time Breakdown (SAI vs Non-SAI)

| Metric                       | Min            | Max            | Average    |
|------------------------------|----------------|----------------|------------|
| Time spent in SAI            | 13.16 sec (ENI 1) | 61.30 sec (ENI 32) | 35.43 sec |
| Time spent outside SAI*      | 27.02 sec (ENI 23) | 39.55 sec (ENI 2)  | 32.75 sec |

\* ZmqConsumer in Orchagent keeps reading and saving the config in parallel to SAI operations

### Analysis

The majority of the growth per ENI programming time was because orchagent cannot leverage the maximum bulk size available. This translates to 13.16 seconds for ENI1 growing to 61.30 seconds for ENI32 spent in SAI and below.

## 3.5 Configuration

The `zmq_sync` flag to `syncd.sh` now disables Redis object creation when set.

# 4 Design

## 4.1 Remove Syncd Redis Objects with ZMQ

When ZMQ notifications are enabled, syncd no longer needs to maintain Redis objects in ASIC DB for notification purposes. This optimization removes the creation and maintenance of these redundant objects, significantly reducing memory footprint.

Reference PR: [#1694 - Remove syncd Redis objects if using ZMQ notifications](https://github.com/sonic-net/sonic-sairedis/pull/1694)

## 4.2 ZMQ Buffer Size Optimization

To accommodate large bulk operations required by DASH workloads, the ZMQ response buffer size was initially increased from 4MB to 64MB ([PR #1660](https://github.com/sonic-net/sonic-sairedis/pull/1660)).

Subsequently, the buffer size was made configurable so each ZMQ consumer/producer service can set an appropriate size based on its requirements ([PR #1697](https://github.com/sonic-net/sonic-sairedis/pull/1697)). This allows services that don't require large buffers to use smaller allocations while syncd and other high-throughput services can use larger buffers.

Reference PRs:
- [#1660 - Increase ZMQ buffer size to accommodate large bulk calls](https://github.com/sonic-net/sonic-sairedis/pull/1660)
- [#1697 - Make ZMQ buffer size adjustable and set it to 4MB by default](https://github.com/sonic-net/sonic-sairedis/pull/1697)

## 4.3 Increase Hugepages for DPU

To support maximum ENI configuration of 64 ENIs on NVIDIA BlueField DPUs, the number of hugepages allocated in memory has been increased from 9216 to 11700.

| Parameter                    | Previous Value | New Value |
|------------------------------|----------------|-----------|
| nr_hugepages (2048kB pages)  | 9216           | 11700     |

Reference PR: [#1696 - Increase the number of hugepages for DPU](https://github.com/sonic-net/sonic-sairedis/pull/1696)

## 4.4 Bulker and Pop Batch Size Optimization

To optimize orchagent memory consumption and increase responsiveness, the bulker size was increased to 64K and pop batch size support was added to the ZMQ consumer. This allows orchagent to process batches of operations more efficiently, reducing memory overhead and improving performance.

Reference PRs:
- [sonic-buildimage #24168 - [DPU] Increase Bulker limit and pop batch size](https://github.com/sonic-net/sonic-buildimage/pull/24168)
- [sonic-swss-common #1084 - Add pop batch size support for ZMQ Consumer](https://github.com/sonic-net/sonic-swss-common/pull/1084)

# 5 Testing

ZMQ Redis tests will continue to emulate the old behavior to track the current state of ASIC programming.

# 6 Future Work

## 6.1 Dynamic Buffer and Bulk Size Configuration

**Problem:** Currently the ZMQ buffer sizes and max bulk size per platform are hard-coded, making it difficult to experiment and adjust values as needed for different platforms.

**Recommendation:** Need the ability to dynamically adjust the buffer sizes and max bulk size per platform to experiment easily and adjust accordingly as needed.

## 6.2 Increase Bulk Size for Improved Performance

**Problem:** Our SAI team recommended a bulk size of at least ~100,000 to achieve < 30 second ENI programming time spent in SAI and below.

**Current Limitation:** Even with increased bulk size, orchagent cannot utilize full bandwidth. This is because orchagent doesn't wait until the complete data has arrived. It greedily picks up the data and calls SAI.

**Existing Optimizations:** Some optimizations related to Route were made in fpmsyncd ([PR #3241](https://github.com/sonic-net/sonic-swss/pull/3241)). It adds a static 500ms delay to let fpmsyncd accumulate Route updates.

**Recommendation:** If the controller knows the number of entries that will be programmed, it should communicate this to orchagent, so it can accumulate entries before calling SAI.

## 6.3 Interleave Post-Processing with SAI Calls

**Problem:** Post-processing operations can be better parallelized with SAI calls to improve throughput.

**Recent Progress:** Recently RingBuffer was added to orchagent to achieve this for Route programming ([PR #3242](https://github.com/sonic-net/sonic-swss/pull/3242)).

**Recommendation:** A similar usage of RingBuffer for DASH object programming can potentially help improve performance.

## 6.4 Investigate Linear Memory Scaling in Orchagent

**Problem:** Orchagent memory is linearly scaling with ENI count. This should be investigated further.

**Expected Behavior:** With optimizations to use jemalloc, removing internal cache to save objects, etc., memory should not linearly scale.

**Action Required:** Investigation needed to identify root cause and implement appropriate memory optimizations.

# 7 References

- [ZMQ Producer/Consumer State Table Design](../sonic-swss-common/ZMQ%20producer-consumer%20state%20table%20design.md)
- [DASH SONiC HLD](../dash/dash-sonic-hld.md)
- [PR #1694: Remove syncd Redis objects if using ZMQ notifications](https://github.com/sonic-net/sonic-sairedis/pull/1694)
- [PR #1660: Increase ZMQ buffer size to accommodate large bulk calls](https://github.com/sonic-net/sonic-sairedis/pull/1660)
- [PR #1697: Make ZMQ buffer size adjustable and set it to 4MB by default](https://github.com/sonic-net/sonic-sairedis/pull/1697)
- [PR #1696: Increase the number of hugepages for DPU](https://github.com/sonic-net/sonic-sairedis/pull/1696)
- [PR sonic-buildimage #24168: [DPU] Increase Bulker limit and pop batch size](https://github.com/sonic-net/sonic-buildimage/pull/24168)
- [PR sonic-swss-common #1084: Add pop batch size support for ZMQ Consumer](https://github.com/sonic-net/sonic-swss-common/pull/1084)
- [PR sonic-swss #3241: fpmsyncd Route accumulation optimization](https://github.com/sonic-net/sonic-swss/pull/3241)
- [PR sonic-swss #3242: RingBuffer for Route programming](https://github.com/sonic-net/sonic-swss/pull/3242)