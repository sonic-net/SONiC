# AINet Testing - Tier1 HLD 

- [AINet Testing - Tier1 HLD ](#ainettesting-tier1hld)
  - [Revision](#revision)
  - [Scope](#scope)
  - [Definitions/Abbreviations](#definitionsabbreviations)
  - [Overview](#overview)
    - [Why AINet Test](#whyainettest)
    - [What AINet Test Validates](#whatainettestvalidates)
    - [Test Strategy](#teststrategy)
  - [High Level Designed](#highleveldesigned)
    - [Topology](#topology)
    - [Control Plane](#controlplane)
    - [Data Plane Implementation Methods](#dataplaneimplementationmethods)
    - [Report](#report)
  - [Requirements](#requirements)
    

---

## Revision

| Rev | Date | Author | Change Description |
| --- | --- | --- | --- |
| 0.1 | 2026-04-27 | Yubin Lee | Initial proposal |

## Scope

This document outlines the AI ​​network access test suite and testing standards, designed to evaluate the performance of chips from ASIC vendors in a broader AI network environment. This **Tier1** document covers functional completeness, scalability and performance, SAI/SDK software maturity, and provides a traffic testing environment based on a traffic generator.

## Definitions/Abbreviations

| Term | Description |
| --- | --- |
| SAI | Switch Abstraction Interface |
| PTF | Packet Test Framework |
| DUT | Device Under Test |
| ECMP | Equal-Cost Multi-Path |
| IFA | In-band Flow Analyzer |
| CRM | Critical Resource Monitoring |
| LPM | Longest Prefix Match |

## Overview

### Why AINet Test

AI fabric switches demand more from ASICs than traditional data center deployments. Lossless RDMA transport, large-scale ECMP forwarding, deep buffer management, and sub-millisecond failover are all baseline requirements — not optional features. A single SAI implementation gap can cause silent packet loss, training job stalls, or cluster-wide performance degradation. AINet testing exists to catch these gaps **before** a chip enters production.

### What AINet Test Validates

AINet Test evaluates ASIC vendor SAI implementations across four dimensions:

| Dimension | Question Answered | Examples |
| --- | --- | --- |
| **Functional Completeness** | Does the SAI implementation correctly support all required features? | L2 forwarding, L3 routing, ACL, QoS, tunneling, host interface traps |
| **Scale and Capacity** | Can the chip hold production-scale table entries simultaneously? | 256K routes + 16K MACs + 16K ARPs + 256×256 ECMP — all at once |
| **Performance** | Does the chip meet throughput and latency baselines under load? | Line-rate forwarding at ≤1600B, 10K routes/s bulk create, flex counter poll ≤500ms avg |
| **Real/Sim AI Traffic** | Real-world AI traffic patterns exhibit strong contextual correlations and complex interdependencies. Given their high sensitivity to network congestion and latency, a critical concern is whether performance degradation or system instability occurs under heavy traffic loads？ | NCCL Test<br>Sim Test（perftest/kccb） |

### Test Strategy

AINet Test Tier1 uses a **layered topology + dual data plane** approach:

*   **Layered Topology**: Five topology options (Topo A–E) allow progressive testing — from minimal single-DUT loopback verification to full DUT + IXIA + auxiliary switch integration. Labs deploy the topology that matches their available hardware; test cases declare which topology they require.
    
*   **Dual Data Plane**: Functional correctness is validated via **PTF raw sockets** (lightweight, no external hardware). Line-rate performance, congestion control, and RDMA flow validation use **IXIA traffic generators** (professional-grade, hardware-accurate).
    

This separation ensures functional tests run anywhere (even with one DUT), while performance tests get hardware-grade accuracy when IXIA is available.

## High Level Designed

### Topology

This document outlines the workflow of the **AINet testing environment**, highlighting its high deployment flexibility. The architecture consists of three core components—the **DUT**, **IXIA tester**, and **Auxiliary equipment**—which can be configured in various combinations to support everything from basic chip verification to large-scale traffic and congestion control simulations.

1.  **System Components** The AINet environment is built upon three primary modules:
    
    *   **DUT** (Device Under Test): The primary device being evaluated.
        
    *   **IXIA Tester**: A high-performance network traffic generator.
        
    *   **Auxiliary Testing Equipment**: This can be either a server or a multi-port switch running SONiC.
        
2.  **Networking Scenarios and Use Cases** The environment can be deployed in three distinct configurations depending on the testing requirements:
    
    *   **Topo A: DUT + Auxiliary Switch** (1 & 3) Setup: The auxiliary equipment is a SONiC switch with at least 32 panel ports. Application: This setup is designed for comprehensive chip-level testing, including basic functional verification, stress testing, and scaling/specification testing.
        
    *   **Topo B: DUT + IXIA + Auxiliary Server** (1, 2, & 3) Setup: The auxiliary equipment functions as a server. Application: This configuration is optimized for large-scale traffic testing, congestion control validation, and CCL (Collective Communication Library) simulation.
        
    *   **Topo C: DUT + IXIA + Auxiliary Switch** (1, 2, & 3) Setup: The auxiliary equipment is a SONiC switch, forming an all-inclusive hardware stack. Application: This serves as an integrated, comprehensive environment capable of executing the full suite of all available test cases.
        
    *   **Topo D: only one DUT** (1) Setup: one DUT and loopback panel port. Application: MVP environment, can run functional test/ stress testing/ scaling test, but need loopback interface.
        
    *   **Topo E: DUT** **+ IXIA** (1 & 2) Setup: one DUT for configuration, IXIA for traffic. Application: Can run traffic testing, congestion control validation, and CCL.
        

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgXbPNZaaVlWN/img/d4efadaf-37b1-4851-903b-90be9579d7b7.png)

### Control Plane

The control plane of this solution leverages the community-standard saiserver framework. As illustrated below, **saiserver** provides a call stack identical to that of syncd, enabling comprehensive verification of the entire path from **syncd** to the SAI, including API performance.

Configurations are managed and deployed via RPC interfaces, supporting operations such as:

```python
self.switch_id = sai_thrift_create_switch(
        self.client, init_switch=True, src_mac_address=ROUTER_MAC,
        port_state_change_notify=None, fdb_event_notify=None,
        switch_shutdown_request_notify=None,
        switch_state_change_notify=None)
self.assertEqual(self.status(), SAI_STATUS_SUCCESS)

sai_thrift_create_route_entry(
        self.client, self.t_route, next_hop_id=self.und_nhop)
```
> Note: All thrift API generated by SAI header automatically.

This implementation enhances the traditional saiserver design by integrating two additional components:

1.  **Pytest + PTF**: This module provides a robust test execution environment. By utilizing a single saiserver Docker container, users can perform seamless, end-to-end test case execution.
    
2.  **RestPy:** This component is primarily used by auxiliary testing equipment to programmatically interface with and control the IXIA tester.
    

### Data Plane Implementation Methods

Regarding the data plane, this document outlines two primary implementation methods: a PTF-based approach for fundamental functional checks and an IXIA-based approach for high-performance traffic modeling and congestion analysis.

1.  **PTF Interface for Functional Verification**
    
    *   Purpose: Primarily used for basic traffic validation and ensuring fundamental connectivity and logic.
        
    *   Scope: Focuses on "sanity checks" and functional correctness of the data path.
        
2.  **IXIA-based Traffic Injection**
    
    *   Purpose: Designed for advanced scenarios such as congestion management validation, executing end-to-end (E2E) traffic models, high-precision latency measurement, and verifying line-rate forwarding performance.
        
    *   Capabilities: IXIA provides industry-standard, professional-grade traffic validation, including:
        
    *   2.1 Data Plane Benchmark Testing
        *   Rich Built-in Packet Templates and Flexible Traffic Pattern Generation.
            *   Support for Ethernet, VLAN, IP, TCP/UDP, VXLAN, GRE, IP-in-IP encapsulations, covering common AI network Underlay and Overlay scenarios.
            *   Fixed/Dynamic/Mixed frame size, fixed/burst rate, and custom flow patterns.
            *   Customizable packet fields (IP, DSCP, ECN, RoCEv2 BTH header) for validating ASIC ACL/QoS policies.
        *   Real-time Throughput, Packet Loss, Out-of-Order Measurement.
            *   Line-rate 100% load zero-loss forwarding validation.
            *   Precise packet loss statistics at any load level.
            *   Out-of-order detection for evaluating ECMP consistency.
        *   Sub-microsecond Level Latency and Jitter Measurement.
            *   Hardware timestamp precision at sub-microsecond level.
            *   Support for both Store-and-Forward and Cut-Through latency measurement modes.
            *   Jitter analysis for evaluating stability of AI training synchronization operations.
        *   Standard RFC Test Methodology to Validate Dataplane Performance.
            *   RFC 2544: Throughput, Latency, Frame Loss Rate, Back-to-Back frames.
            *   RFC 2889: Switch forwarding performance (HoL blocking, address learning rate, error frame filtering, etc.).
            *   RFC 3918: Multicast throughput and forwarding latency.

    *   2.2 Control Plane Protocol Simulation
        *   Simulate IGP/EGP Peers to Validate Control Plane Performance.
            *   Large-scale neighbor simulation to validate control plane scalability.
            *   Large-scale route items and topology injection to validate RIB(Routing Information Base) and FIB(Forwarding Information Base) table scalability.
            *   Control plane and data plane table consistency validation.
        *   Stability Testing on Control Plane.
            *   Periodic route advertisement/withdrawal to validate the load and forwarding stability.
            *   Routing session frequent Up/Down simulation to validate Graceful Restart and BFD fast detection mechanisms.
            *   Negative test for the robustness.
        *   High Availability and Convergence Testing.
            *   ECMP load balance validation to prevent single-link congestion degrading AI workload efficiency.
            *   Multi-VRF/EVPN instance simulation to validate route leak prevention between AI clusters.
            *   Quantified route convergence time after link/node failure.

    *   2.3 Stateful RoCEv2 Performance Validation
        *   RoCEv2 Session Emulation
            *   Complete stateful RoCEv2 connection establishment.
            *   Large-scale QP(Queue Pair) sessions to validate ECMP load balance.
            *   Long-duration RoCEv2 Elephant flow to full fill the link bandwidth.
        *   Lossless Network Validation
            *   Generate and response to PFC(Priority Flow Control) frame to validate XON/XOFF triggers in ASIC.
            *   End-to-end CNP, ACK, NACK, and retransmission reactions to assist ASIC ECN marking test.
            *   Lossless network validation in In-cast, All-to-All, and Many-to-Many topology
        *   Performance Metrics
            *   Data plane metrics like flow rate, packet loss, latency, retransmitted frames, and JCT(Job Completion Time).
            *   Control plane metrics like ECN, CNP, ACK, NACK for better debugging.
            *   General performance results in different flow control mechanisms.

    *   2.4 Collective Communication Traffic Benchmark
        *   Micro-benchmark Test
            *   AllReduce, AlltoAll, AllGather, ReduceScatter, Broadcast for single and multiple ASICs test.
            *   Flexible to control the Data Size, Message Size, NPU interconnect bandwidth to create various scenarios.
            *   Per-chunk, per-flow tracking for analysis.
            *   Percentile, JCT, AlgBW, BusBW statistics to make the performance visible.
        *   Multi-tenant Performance Isolation for AI workload
            *   Run multiple kinds of CCLs in parallel to validate the performance impact between each other.
            *   Long-duration multiple CCLs in parallel to validate the performance impact with time elapse.
        *   AI Workload Emulation
            *   Replay the real-world AI workloads to generate a more complex CCL sequence.
            *   Overlaying multiple AI workloads on the same network to validate the performance impact between each other.


### Report

For Basic Funtion：

| SAI\_ATTR | Testcase | read | create | set |
| --- | --- | --- | --- | --- |
| SAI\_PORT\_ATTR\_OPER\_STATUS | saiport.py::testxxx | Y | No Need | No Need |
| SAI\_PORT\_ATTR\_PORT\_VLAN\_ID | saiport.py::testxxx | Y | Y | N |
| SAI\_PORT\_ATTR\_DEFAULT\_VLAN\_PRIORITY | NA | No Test | No Test | No Test |

For Scale/Performance

| scale |  |
| --- | --- |
| ECMP group | 1024 |
| ECMP member | 65535 |
| IPv4 prefixes | 1048576 |
| IPv6 prefixes | 840884 |

| L3 Performance | create perf rps | remove perf rps |
| --- | --- | --- |
| IPv4 /16-bit Deployment | 28980.17 | 44670.78 |
| IPv4 /24-bit Deployment | 28683.17 | 43309.43 |

TBD： IXIA test result

## Requirements