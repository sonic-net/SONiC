# Tier 1 - Ranking Test HLD 

---

## Revision

| Rev | Date | Author | Change Description |
| --- | --- | --- | --- |
| 0.1 | 2026-05-12 | Yubin Lee | Initial proposal |

## Scope

The Ranking Test project aims to establish a standardized, vendor-neutral evaluation framework designed to benchmark data center switching ASICs. By leveraging the Switch Abstraction Interface (SAI), the framework isolates the hardware’s raw capabilities from the SONiC system. The ultimate goal is to provide an "apple-to-apple" comparison to support strategic chip selection and integration.

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

### Why Ranking Test?

The Ranking Test is essential for two primary reasons:

*   **Risk Shift-Left**: Discovering hardware defects or performance bottlenecks in the late stages of a project is extremely costly and difficult to resolve. Ranking Test "shifts risk left" by identifying silicon-level bugs and scale limitations early, ensuring that fundamental hardware issues are addressed before full-system deployment.
    
*   **Decoupling Software Dependencies**: Traditional switch testing relies on a complete SONiC, which is typically unavailable during the early stages of silicon development. By utilizing the SAI layer, the Ranking Test enables "bare-metal" evaluation of the chip's core capabilities without waiting for a fully integrated software stack.
    
*   **Unified Reporting for Vendor Alignment**: Empowers cloud providers to communicate and negotiate with silicon vendors using a common result report. 
    

#### Core Objectives

*   Standardized Benchmarking: Utilize **SAI** as a universal abstraction layer to ensure that test cases are portable and execution results are comparable across different silicon architectures.
    
*   Minimalist Test Environment: Develop a "lean" execution stack consisting only of the silicon, driver/SDK, and SAI layer, eliminating performance interference caused by SONiC control plane overhead.
    
*   Comprehensive Performance Profiling: Deliver a multi-dimensional scorecard covering functionality, hardware scale, control-plane efficiency, and data-plane throughput.
    

### In-Scope Evaluation Dimensions

1.  **Fundamental ASIC Functionality**
    
    *   Validation of core L2/L3 features, VLAN, ACL, and QoS mapping through standard SAI APIs.
        
    *   Verification of advanced telemetry features (e.g., Mirroring, INT) at the silicon level.
        
2.  **Hardware Scale and Scalability**
    
    *   Stress testing of hardware table capacities, including L3 Routing tables (LPM/Host), MAC tables, ECMP groups, and ACL rule depth.
        
    *   Assessment of resource utilization and collision behavior under maximum scale.
        
3.  **Control Plane Table Programming Performance**
    
    *   Measurement of the "Table Insertion Rate" (flow setup per second) via SAI.
        
    *   Evaluation of SDK stability during massive, high-speed table updates.
        
4.  **Data Plane and Traffic Analysis (IXIA Integration)**
    
    *   Throughput & Latency: Validating 100% line-rate forwarding and measuring sub-microsecond latency/jitter across various packet sizes.
        
    *   Congestion & Buffer Management: Using IXIA to simulate Incast scenarios to evaluate buffer allocation, ECN (Explicit Congestion Notification) marking accuracy, and PFC (Priority Flow Control) headroom efficiency.
        

## Test Framework Designed

### Topology

This document outlines the workflow of the **Ranking testing environment**, highlighting its high deployment flexibility. The architecture consists of three core components—the **DUT**, **IXIA tester**, and **Auxiliary equipment**—which can be configured in various combinations to support everything from basic chip verification to large-scale traffic and congestion control simulations.

1.  **System Components** The environment is built upon three primary modules:
    
    1.  **DUT** (Device Under Test): The primary device being evaluated.
        
    2.  **IXIA Tester**: A high-performance network traffic generator.
        
    3.  **Auxiliary Testing Equipment**: This can be either a server or a multi-port switch running SONiC.
        
2.  **Networking Scenarios and Use Cases** The environment can be deployed in three distinct configurations depending on the testing requirements:
    
    *   **Topo A: DUT + Auxiliary Switch** (1 & 3) Setup: The auxiliary equipment is a SONiC switch with at least 32 panel ports. Application: This setup is designed for comprehensive chip-level testing, including basic functional verification, stress testing, and scaling/specification testing.
        
    *   **Topo B: DUT + IXIA + Auxiliary Server** (1, 2, & 3) Setup: The auxiliary equipment functions as a server. Application: This configuration is optimized for large-scale traffic testing, congestion control validation, and CCL (Collective Communication Library) simulation.
        
    *   **Topo C: DUT + IXIA + Auxiliary Switch** (1, 2, & 3) Setup: The auxiliary equipment is a SONiC switch, forming an all-inclusive hardware stack. Application: This serves as an integrated, comprehensive environment capable of executing the full suite of all available test cases.
        

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4maOgXbPNZaaVlWN/img/d4efadaf-37b1-4851-903b-90be9579d7b7.png)

### Control Plane

The control plane of this solution leverages the community-standard saiserver framework. As illustrated below, **saiserver** provides a call stack identical to that of syncd, enabling comprehensive verification of the entire path from **syncd** to the SAI, including API performance.

> saiserver docker will update and intergration to SONiC system with  SAITHRIFT\_V2=y flag

> DUT can run without SONiC or with SONiC

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
    
    *   Purpose: Designed for advanced scenarios such as congestion management validation, executing end-to-end (E2E) traffic models, and verifying line-rate forwarding performance.
        
    *   **Capabilities**: IXIA provides industry-standard, professional-grade traffic validation, including:
        
        *   Dataplane benchmark testing
            
        *   Control plane protocol simulation
            
        *   Stateful RoCEv2 performance testing
            
        *   Collective Communication traffic pattern generation
            
        *   AI workload emulation
            

## Test cases

### Basic Cases

Basic SAI attribute test, including almost all SAI definition,L2, L3, QoS, Buffer, ACL, Tunnel, SRv6.

420+ cases covering LAG, Route, RIF, VLAN, VRF already have.

| Feature | Case number |
| --- | --- |
| NextHop | 25 |
| NextHopGroup | 28 |
| Rif | 100+ |
| Vrf | 24 |
| Vlan | 40 |
| ... | ... |

### Scale & Performance Cases

*   For L2, we test FDB learning rate/flush rate, L2 scale with random Mac inject, VLAN create and delete rate, VLAN scale
    
*   For L3, we have Route fill rate test with different Router pattern (in order or random, different prefixes), we have Route performance test, we have ECMP/member scale test, we have rif/vrf/subif scale and performance test
    
*   We have counter read performance test including ACL/PORT/QUEUE/PG.. 
    
*   60+ testcases already have，and all scale is got by SAI query or SAI get, so that we can get SAI real scale and test it.
    

| 文件 | case |
| --- | --- |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleMask16Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleMask24Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleMask26Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleMask32Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleSetTest |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopMixScale1Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopMixScale2Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleIterate1Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleIterate2Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4SingleHopScaleIterate4Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleMask48Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleMask56Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleMask64Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleSetTest |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopMixScale1Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleIterate1Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleIterate2Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv6SingleHopScaleIterate4Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4IPv6MixSingleHopScale1Test |
| ext\_sai\_l3\_route\_scale\_test.py | L3IPv4IPv6MixSingleHopScale2Test |
| ... | ... |

### Feature Test

*   HPN feature, including lossy/ lossess/ ECN/ PFC/ Buffer isolate/ minibuffer
    
*   ACL enhancement cases
    
*   IFAv2 cases
    
*   _Easily to create a new private feature on demand_
    

| saibufferqos.py | SaiHelperScaleTM |
| --- | --- |
| saibufferqos.py | LossyAlphaTest |
| saibufferqos.py | LossyEcnTest |
| saibufferqos.py | LossyWredTest |
| saibufferqos.py | LossyMinGarenteeTest |
| saibufferqos.py | LossyCPUTest |
| saibufferqos.py | LossyPfcRxTest |
| saibufferqos.py | LossySrcBalancingTest |
| saiifa\_extend.py | IFAv2TransitMultiAclEntryStressTest |
| saiifa\_extend.py | IFAv2TransitNodeForwardNonIFAPktTest |
| saiifa\_extend.py | IFAv2TransitNodeUsingIntAclTableTest |
| saiacl\_extend.py | AclTableTypeTestIgr |
| saiacl\_extend.py | AclTableTypeTestEgr |
| saiacl\_extend.py | AclQsetBthopcodeTest |
| saiacl\_extend.py | AclQsetAethsyndromeTest |

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

## Target

1.  Create a new dir "Ranking Test" in **sonic-mgmt** repo
    
2.  Push all test cases and test framework in it.