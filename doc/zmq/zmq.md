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
- [3 Syncd Changes](#3-syncd-changes)
  * [3.1 Syncd Flow](#31-syncd-flow)
  * [3.2 After the Changes](#32-after-the-changes)
  * [3.3 Memory Footprint Comparison](#33-memory-footprint-comparison)
- [4 Design](#4-design)
  * [4.1 Remove Syncd Redis Objects with ZMQ](#41-remove-syncd-redis-objects-with-zmq)
  * [4.2 ZMQ Buffer Size Optimization](#42-zmq-buffer-size-optimization)
  * [4.3 Increase Hugepages for DPU](#43-increase-hugepages-for-dpu)
  * [4.4 Configuration](#44-configuration)
- [5 Testing](#5-testing)
- [6 References](#6-references)

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

# 1 Overview

## 1.1 Introduction and Scope

For almost all production versions of SONiC, syncd manages ASIC objects by reading changes to the ASIC_DB Redis database and applying them over SAI, then writing the result back to ASIC_DB. The one exception to this was the SmartSwitch DPU version of SONiC, which read the changes over ZMQ but also wrote the state and results to ASIC_DB. This led to some failures in scale testing as DPUs have less memory than most switches and could not handle copying the database during show techsupport, as well as running out of memory when attempting to create the DPU maximum scale of 64 ENIs. We decided to optimize by effectively removing the Redis database from DPU SONiC entirely and only using the ZMQ notifications to track ASIC object updates.

## 1.2 Benefits of this Feature

The optimization removes unnecessary Redis objects from syncd to save on memory, which is smaller on DPU SONiC, necessitating this change. These objects are instead ZMQ notifications that are removed from memory after being programmed by SAI, but are recorded in SAI record files. This both reduced memory consumption for ENIs (which exceeded 64 GB for 64 ENIs), and decreased the time spent per operation in syncd as the Redis calls were removed.


# 2 Requirements

## 2.1 Functional Requirements

- When ZMQ notifications are enabled, syncd shall not create Redis notification objects in ASIC DB
- The optimization shall be transparent to orchagent and other consumers
- No functionality shall be lost when this optimization is enabled

# 3 Syncd changes

## 3.1 Syncd flow

Notifications prior to the change were tracked by ZMQ Push/Pull sockets. State in ASIC_DB is updated only after the ASIC is successfully programmed. `sairedis.rec` is also updated with an entry that includes the SAI call and its response code.


## 3.2 After the changes

The only major change is that objects cannot be created or destroyed in zmq_sync notification mode.

## 3.3 Memory Footprint Comparison

**64 ENI Test Results:**

| Parameter                    | Previous Value | New Value |
|------------------------------|----------------|-----------|
| Used Memory                  | > 64 GB        | 44.99 GB  |
| VmRSS syncd                  | 23.3 GB        | 2.61 GB   |

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

## 4.4 Configuration

The `zmq_sync` flag to `syncd.sh` now disables Redis object creation when set.

# 5 Testing

ZMQ Redis tests will continue to emulate the old behavior to track the current state of ASIC programming.

# 6 References

- [ZMQ Producer/Consumer State Table Design](../sonic-swss-common/ZMQ%20producer-consumer%20state%20table%20design.md)
- [DASH SONiC HLD](../dash/dash-sonic-hld.md)
- [PR #1694: Remove syncd Redis objects if using ZMQ notifications](https://github.com/sonic-net/sonic-sairedis/pull/1694)
- [PR #1660: Increase ZMQ buffer size to accommodate large bulk calls](https://github.com/sonic-net/sonic-sairedis/pull/1660)
- [PR #1697: Make ZMQ buffer size adjustable and set it to 4MB by default](https://github.com/sonic-net/sonic-sairedis/pull/1697)
- [PR #1696: Increase the number of hugepages for DPU](https://github.com/sonic-net/sonic-sairedis/pull/1696)
