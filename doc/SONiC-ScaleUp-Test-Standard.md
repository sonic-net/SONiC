# SONiC Scale-Up Test Standard

**Document Version:** Draft v0.4  
**Draft Date:** 02/Jun/26  
**Working Group:** SONiC Scale Up WG - Test Subgroup  
**Author:** SONiC Scale Up Test Subgroup (Alibaba, Broadcom, ByteDance, Keysight, Univista)

---

## Table of Contents

- [1. Scope & Objectives](#1-scope--objectives)
- [2. References](#2-references)
- [3. Test Environment & Topology](#3-test-environment--topology)
  - [3.1 Hardware Platform](#31-hardware-platform)
  - [3.2 Switch Topology & SAI Configuration](#32-switch-topology--sai-configuration)
- [4. Unified Test Specifications (LLR & CBFC)](#4-unified-test-specifications-llr--cbfc)
  - [4.1 LLR Unified Test Cases](#41-llr-unified-test-cases)
  - [4.2 CBFC Unified Test Cases](#42-cbfc-unified-test-cases)
- [5. Pairwise Interop Matrix](#5-pairwise-interop-matrix)
- [6. Data Collection & Pass/Fail Criteria](#6-data-collection--passfail-criteria)
  - [6.1 Data Recording Format](#61-data-recording-format)
  - [6.2 Pass/Fail Criteria](#62-passfail-criteria)
- [7. Definitions & Abbreviations](#7-definitions--abbreviations)
- [8. Deliverables Checklist](#8-deliverables-checklist)
- [9. Missing SAI APIs & Coverage Gaps](#9-missing-sai-apis--coverage-gaps)

---

## Revision History

| Revision | Date | Description |
| :--- | :--- | :--- |
| 0.1 | 06/May/26 | Initial version |
| 0.2 | 11/May/26 | Topology simplification (4-port), Scope refinement (LLR/CBFC only) |
| 0.3 | 22/May/26 | Integrated LLR/CBFC SAI test framework & unified test cases |
| 0.4 | 02/Jun/26 | Refined LLR/CBFC test cases with hardware counter verification, protocol state machine focus, boundary packet testing, and generalized hardware roles. |

---

## 1. Scope & Objectives

This draft aims to define standardized test methods, pass/fail criteria, and data collection specifications for **LLR (Link Level Retry)** and **CBFC (Credit-Based Flow Control)** in SONiC Scale-Up networks.

**Core Objectives:**
- Unify SAI extension attribute definitions and capability query interfaces.
- Establish a standardized test case matrix for data plane and control plane.
- Define clear Pass/Fail thresholds and data collection formats.
- Provide standard compliance/performance test results and deployment recommendations for scale-up users.

---

## 2. References

| Category | Document/PR | Version/Status |
|------|---------|-----------|
| **UEC Spec** | UEC Scale-Up Spec v1.0 | Ref: §4.3 (LLR), §6 (CBFC) |
| **SAI Extensions** | PR #2225 (LLR), #2263 (CBFC) | Draft / Review |
| **Historical Cases** | SONiC-Scale-Up-LLR-CBFC-Test-Proposal.xlsx | Keysight |
| **Historical Cases** | UV_ORI_005_SUE_Protocol_UEC-TF1_Network_Report.pdf | Univista |

---

## 3. Test Environment & Topology

### 3.1 Hardware Platform
- **DUT (Switch):** Must support SAI LLR/CBFC extensions.
- **Tester:** Must support LLR/CBFC traffic models, sub-microsecond timestamps, CRC error injection.
- **Endpoints:** Must support LLR/CBFC protocol stack, acting as peer or sink.

### 3.2 Switch Topology & SAI Configuration
To verify flow control and retry mechanisms in Scale-Up scenarios, a **multi-layer topology** is adopted. This setup supports flexible switching configurations.

**Topology Diagram:**

```text
                  [ Tester ] (Traffic Generator)
                  /                        \
          Port 1 /                          \ Port 2
                / (Source/Sink)              \ (Source/Sink)
               /                              \
              /                                \
     ┌──────────────────────────────────────────────────┐
     │                 Switches (Layer 1)               │
     │               (Running SAI LLR/CBFC)             │
     └──────────────────────────────────────────────────┘
      \                                /
       \                              /
        \                            /
         \                          /
          v                        v
     ┌──────────────────────────────────────────────────┐
     │                 Switches (Layer 2)               │
     │               (Running SAI LLR/CBFC)             │
     └──────────────────────────────────────────────────┘
      \                                  /
       \ Port 3 (Source/Sink)  Port 4 (Source/Sink) /
        \                              /
         \                            /
          \                          /
           v                        v
    ┌──────────────────┐    ┌──────────────────┐
    │    Endpoint 1    │    │    Endpoint 2    │
    └──────────────────┘    └──────────────────┘
```

**Topology Description:**
- **Physical Connection:** Tester connects to Spine switches; Endpoints connect to Leaf switches.
- **Port Assignment:**
  - **Port 1 & 2:** Tester (Source/Sink)
  - **Port 3 & 4:** Endpoint (Source/Sink)
- **SAI Configuration:**
  - **LLR/CBFC Attributes:** Configured via `sai_set_port_attribute` on the Switch.
  - **Capability Query:** Use `sai_query_port_attribute_capability` to verify hardware support for LLR timeout resolution and CtlOS spacing.
  - **Stats Counters:** Read via `sai_get_port_stats` to verify retry counts and credit starvation.

**Traffic Model:**
- **1-to-1 Basic Verification:**
  - Port 1 ↔ Port 2 (Intra-Side)
  - Port 3 ↔ Port 4 (Intra-Side)
  - Port 1 ↔ Port 4 (Cross-Side)
- **2-to-2 Symmetric Traffic:**
  - (Port 1 + Port 3) ↔ (Port 2 + Port 4)
- **2-to-1 or 3-to-1 Incast:**
  - (Port 2 + Port 3 + Port 4) → Port 1
- Verifies CBFC fairness and LLR retransmission efficiency.

---

## 4. Unified Test Specifications (LLR & CBFC)

This section integrates functional requirements (UEC) with SAI API/Data Plane verification.

### 4.1 LLR Unified Test Cases

| Case ID | Functional Goal (UEC) | SAI Configuration (API) | Traffic Injection (Data Plane) | Verification Criteria (Stats/Trace) |
|:---|:---|:---|:---|:---|
| **LLR-01** | **Basic LLR Sequence/ACK** | Set `LLR_MODE_LOCAL=true`<br>`LLR_MODE_REMOTE=true` | Inject N=100 LLR frames with good seq and crc from one test port | Read attribute returns `true`; HW engine active<br>No traffic loss<br>`LLR_RX_OK=N` on DUT Rx port<br>`LLR_TX_OK=N` on DUT Tx port<br>Test port LLR counters match DUT LLR counters |
| **LLR-02** | **Retry (NACK)** | 1. Enable LLR<br>2. Clear counters | 1. Inject N=100 frames from one test port<br>2. Simulate one LLR frame drop to generate NACK from other test port | `LLR_RX_NACK_CTL_OS=1` and `LLR_RETRY_COUNT=1` on DUT Tx port <br>Check tester Rx port counters for valid replay<br>No traffic loss|
| **LLR-03** | **Retry (Replay timer expired)** | Set `REPLAY_COUNT_MAX=3` | 1. Scenario A: Block ACKs continuously on one test port<br>Scenario B: Freeze sequence in ACKs continuously on one test port <br>2. Inject N=100 frames from the other test port | After 3 retries, packet dropped; State → FLUSH | 
| **LLR-04** | **NACK generation** | 1. Enable LLR<br>2. Clear counters | Two scenarios: <br>1. Inject N=1000 LLR frames with 1 bad CRC frame<br>2. Inject N=1000 LLR frames with seq gap simulation once |1. `LLR_RX_EXPECTED_SEQ_BAD = 1` (only for scenario 1), `LLR_TX_NACK_CTL_OS=1` and `LLR_RX_REPLAY = 1` on DUT Rx port<br>2. No traffic loss <br>3. No out of order reception of traffic |
| **LLR-05** | **Poison CRC Handling** | 1. Enable LLR<br>2. Clear counters | 1. Inject N=100 frames from one test port <br>2. Simulate one LLR frame with poison CRC among these frames | `LLR_RX_EXPECTED_SEQ_POISONED=1`, `LLR_TX_NACK_CTL_OS=0`, `LLR_RX_REPLAY=0`,  on DUT Rx port <br>Test port LLR counters match DUT LLR counters| 
| **LLR-06** | **OUTSTANDING_FRAMES_MAX Limit** | Set `OUTSTANDING_FRAMES_MAX=4`, `FLUSH_LLR_FRAME_ACTION=LLR_FRAME_ACTION_DISCARD` | 1. Drop ACK Rx on one test port. <br>2. Send N=100 frames from other test port | DUT attempts to replay only 4 frames before going to FLUSH state |
| **LLR-07** | **Buffer Capacity** | 1. Enable LLR<br>2. Clear counters | 1. In one test port simulate CtlOS delay equivalent to 500m RTT <br>2. From the other test port inject N frames at max frame size at 100% line rate. Repeat with min frame size | 1. No traffic loss<br>2. LLR traffic received at 100% line rate on the test port where delay is simulated 
| **LLR-08** | **Flush Recovery** | Set `RE_INIT_ON_FLUSH=true` | Force FLUSH state | Auto triggers Re-INIT; Link recovers |
| **LLR-09** | **Packet Size Traversal** | Enable LLR | Inject traffic with varying frame sizes including, but not limited to - 64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,9216+x bytes where x is 0, +1 or -1 (except for 64 bytes +1 only and for 9216 bytes -1 only) | Verify LLR functions correctly across all sizes; No abnormal drops|
| **LLR-10** | **Handling of LLR and non-LLR Frames together** | Enable LLR | Two Scenarios: <br>1. Inject N frames with both LLR and non-LLR frames (no error) <br>2. Inject N frames with both LLR and non-LLR frames (Inject uncorrectable FEC errors at the same time) | 1. Verify DUT Rx port can correctly process both type of frames <br>2. Expect no traffic loss in scenario 1 <br> Expect loss in non-LLR frames, but no loss in LLR frames in scenario 2 <br>3. Latency of LLR and non-LLR frames should be comparable in scenario 1 |

### 4.2 CBFC Unified Test Cases

| Case ID | Functional Goal (UEC) | SAI Configuration (API) | Traffic Injection (Data Plane) | Verification Criteria (Stats/Trace) |
|:---|:---|:---|:---|:---|
| **CBFC-01** | **Sender Credit Handling** | Enable CBFC Sender on DUT Tx port| Inject N frames with varying frame sizes including, but not limited to - 64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,9216+x bytes where x is 0, +1 or -1 (except for 64 bytes +1 only and for 9216 bytes -1 only) | VC counters `SENDER_CREDITS_USED`, `SENDER_CREDITS_CONSUMED`, `SENDER_CREDITS_FREED` on DUT Tx port matches theoretical formula |
| **CBFC-02** | **Receiver Credit Handling** | Enable CBFC Receiver on DUT Rx port | Inject N frames with varying frame sizes including, but not limited to - 64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,9216+x bytes where x is 0, +1 or -1 (except for 64 bytes +1 only and for 9216 bytes -1 only) | VC counters `RECEIVER_CREDITS_CONSUMED`, `RECEIVER_CREDITS_FREED` on DUT Tx port matches theoretical formula |
| **CBFC-03** | **Credit Loss/Recovery** | Enable CBFC | 1. Stop sending CC_Update message and then inject 100 corrupted packets <br>2. Resume CC_Update messages | Check VC counters `RECEIVER_CREDITS_CONSUMED` and `RECEIVER_CREDITS_FREED` on DUT Rx port <br>1. After step 1, there is no change in these counters. <br>2. After step 2, these counters are updated and matches S_VC_CC and S_VC_CF of Sender test port. Additionally S_P_CU = 0 on Sender test port. |
| **CBFC-04** | **Backpressure** | Enable CBFC | 1. From one test port inject traffic at 100% line rate with different frame sizes including, but not limited to - 64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,9216+x bytes where x is 0, +1 or -1 (except for 64 bytes +1 only and for 9216 bytes -1 only) <br>2. From other test port, create backpressure by changing VC drain rate| 1. DUT propagates backpressure upstream and traffic gets flow controlled.<br> - When drain rate is 100%, observed traffic throughput is maximum.<br> - When drain rate is 0%, traffic pauses. <br> - When drain rate is 50%, traffic flows at a rate lower than 100% but higher than 0% <br>2. No traffic loss observed due to backpressure|
| **CBFC-05** | **VLAN PCP+DEI Mapping** | Configure VLAN mapping | Send tagged traffic | Traffic enters lossless VC mapped to VLAN PCP + DEI bits |
| **CBFC-06** | **IPv4 DSCP Mapping** | Configure DSCP mapping | Send DSCP-marked traffic | Traffic enters lossless VC mapped to IPv4 DSCP bits |
| **CBFC-07** | **IPv6 DSCP Mapping** | Configure IPv6 DSCP mapping | Send IPv6 DSCP-marked traffic | Traffic enters lossless VC mapped to IPv6 DSCP bits |
| **CBFC-08** | **Per-VC Credit** | Configure 2 lossless VCs in per VC credit mode | 1. Inject traffic on both VCs. <br>2. Create backpressure on individual VCs. | Backpressure on VC1 does not affect traffic flow at VC2 |
| **CBFC-09** | **Per-Port Credit** | Configure 2 lossless VCs in per port credit mode | 1. Inject traffic on both VCs. <br>2. Create backpressure on individual VCs. | 1. Traffic flows at VCs are not affected when no backpressure <br>2. Depending upon implementation, backpressure on VC1 might or might not affect traffic flow at VC2  |
| **CBFC-10** | **N-to-1 Incast with lossless traffic** | Enable CBFC | Inject N-source incast lossless traffic at 100% line rate| 1. Flow control triggered<br>2. No loss
| **CBFC-11** | **N-to-1 Incast with lossless + best effort traffic** | Enable CBFC | Inject N-source incast lossless + best effort traffic at 100% line rate | 1. No loss for lossless traffic<br>2. BE VC: Normal degradation |
| **CBFC-12** | **Buffer Capacity** | Enable CBFC | 1. In one test port simulate CtlOS delay equivalent to 500m RTT <br>2. From the other test port inject max frame size lossless traffic at 100% line rate. Repeat with min frame size | 1. No traffic loss<br>2. Lossless traffic received at 100% line rate on the test port where delay is simulated 

---

## 5. Pairwise Interop Matrix

| Test Scenario | Participating Devices | Traffic Direction | Verification Focus | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Scenario A** | **Broadcom + Tester** | Ixia ↔ Broadcom | LLR/CBFC standard behavior baseline verification | Keysight / Alibaba |
| **Scenario B** | **Broadcom + Prototype** | Univista ↔ Broadcom | Vendor protocol stack interoperability | Univista / Alibaba |
| **Scenario C** | **Tester + Prototype** | Ixia ↔ Univista | Direct interop verification between tester and prototype | Keysight / Univista |
| **Scenario D** | **Multi-Source Incast** | Ixia(2) + Univista(2) | Flow control fairness & LLR efficiency under multi-source incast | All |

---

## 6. Data Collection & Pass/Fail Criteria

### 6.1 Data Recording Format
All tests must record the following fields (CSV/JSON format):
```csv
Timestamp, Scenario_ID, Frame_Size, Source_IP, Dest_IP, Test_Case, Config_Params, Expected_Value, Measured_Value, Pass/Fail, Notes
```

### 6.2 Pass/Fail Criteria
- **API/Control Plane:** Attribute read/write consistency, error codes comply with SAI spec → `PASS`
- **Data Plane/Performance:** Measured vs Theoretical deviation < 5%, or meets UEC spec thresholds → `PASS`
- **Interop:** Consistent flow control/retry behavior across multi-vendor combos, no deadlocks/abnormal packet loss → `PASS`

---

## 7. Definitions & Abbreviations

| Term | Definition |
| :--- | :--- |
| **LLR** | Link Level Retry — a hardware-based retransmission mechanism that corrects link-layer errors without involving the host. |
| **CBFC** | Credit-Based Flow Control — a credit-based mechanism that prevents packet drops by pausing traffic when the receiver's buffer is near capacity. |
| **UEC** | Ultra Ethernet Consortium — the standards body defining the Scale-Up network specifications referenced in this document. |
| **SAI** | Switch Abstraction Interface — the vendor-neutral API layer used to configure switch ASIC features. |
| **DUT** | Device Under Test — the switch being tested. |
| **VC** | Virtual Channel — a logical traffic lane within a physical port, used to isolate lossless and best-effort traffic. |
| **NACK** | Negative Acknowledgement — a control signal indicating a frame was received in error and replay is requested. |
| **CtlOS** | Control Ordered Set — an out-of-band signaling unit used by LLR and CBFC for ACK/NACK and credit updates. |
| **FEC** | Forward Error Correction — a physical-layer error correction mechanism. |
| **CRC** | Cyclic Redundancy Check — a frame integrity check field. |
| **RTT** | Round-Trip Time — the time for a signal to travel from sender to receiver and back. |
| **BE** | Best Effort — a traffic class that may be dropped under congestion. |
| **DSCP** | Differentiated Services Code Point — a field in the IP header used for traffic classification. |
| **PCP** | Priority Code Point — a 3-bit field in the 802.1Q VLAN tag used for traffic prioritization. |
| **DEI** | Drop Eligible Indicator — a 1-bit field in the 802.1Q VLAN tag. |

---

## 8. Deliverables Checklist

| Deliverable | Content Requirement | Owner | Status |
|--------|----------|--------|------|
| SAI Attribute Final Definition Table | Includes all LLR/CBFC R/W attributes, enums, counters | Broadcom | Pending |
| Test Case Matrix V1.0 | Covers API/Data/Stats, includes Pass/Fail criteria, **includes frame size & boundary tests** | All | Pending |
| Multi-Source Test Config Manual | DUT version, Tester config, cabling diagram, traffic ratios | Keysight/Univista/Broadcom | Pending |
| Data Recording Template | CSV/JSON Schema + Examples | Alibaba/Bytedance | Pending |
| Joint Test Schedule | Clear execution windows & resource allocation for each scenario | All | Pending |

---

## 9. Missing SAI APIs & Coverage Gaps

Based on the UEC Scale-Up specification and current SAI PRs (#2225, #2263), the following SAI attributes and counters are identified as **missing** or **not fully covered** by the current test cases. These should be discussed with the SAI vendor for inclusion in the final implementation.

| Missing SAI Attribute/Counter | Expected Type | Description / Usage in v0.4 |
| :--- | :--- | :--- |
| **SAI_PORT_ATTR_LLR_MODE_LOCAL** | bool | LLR-01: Enable local LLR mode. |
| **SAI_PORT_ATTR_LLR_MODE_REMOTE** | bool | LLR-01: Enable remote LLR mode. |
| **SAI_PORT_ATTR_LLR_REPLAY_COUNT_MAX** | uint32_t | LLR-03: Max replay attempts before flush. |
| **SAI_PORT_ATTR_LLR_OUTSTANDING_FRAMES_MAX** | uint32_t | LLR-06: Limit outstanding retransmissions. |
| **SAI_PORT_ATTR_LLR_FLUSH_FRAME_ACTION** | sai_llr_frame_action_t | LLR-06: Action on flush (DISCARD/REPLAY). |
| **SAI_PORT_ATTR_LLR_RE_INIT_ON_FLUSH** | bool | LLR-08: Auto re-init after flush. |
| **SAI_PORT_STAT_LLR_RX_OK** | uint64_t | LLR-01/05: Count of successfully received LLR frames. |
| **SAI_PORT_STAT_LLR_TX_OK** | uint64_t | LLR-01: Count of successfully transmitted LLR frames. |
| **SAI_PORT_STAT_LLR_RX_NACK_CTL_OS** | uint64_t | LLR-02/04: Count of NACK CtlOS generated. |
| **SAI_PORT_STAT_LLR_RX_EXPECTED_SEQ_BAD** | uint64_t | LLR-04: Count of sequence errors detected. |
| **SAI_PORT_STAT_LLR_RX_EXPECTED_SEQ_POISONED** | uint64_t | LLR-05: Count of Poison CRC detected. |
| **SAI_QUEUE_ATTR_CBFC_CREDIT_SIZE** | uint64_t | CBFC-01/02: Current credit pool size. |
| **SAI_QUEUE_STAT_CBFC_SENDER_CREDITS_USED** | uint64_t | CBFC-01: Credits consumed by sender. |
| **SAI_QUEUE_STAT_CBFC_SENDER_CREDITS_FREED** | uint64_t | CBFC-01: Credits returned/freed by sender. |
| **SAI_QUEUE_STAT_CBFC_RECEIVER_CREDITS_CONSUMED** | uint64_t | CBFC-02/03: Credits consumed by receiver. |
| **SAI_QUEUE_STAT_CBFC_RECEIVER_CREDITS_FREED** | uint64_t | CBFC-02/03: Credits freed by receiver. |
| **SAI_PORT_ATTR_LLR_CTL_OS_MAX_SPACING** | uint32_t | UEC spec requires Max CtlOS spacing. |
| **SAI_PORT_ATTR_LLR_REPLAY_BUFFER_SIZE** | uint32_t | Required to configure replay buffer depth. |
| **SAI_PORT_ATTR_LLR_CAPABILITY** | sai_port_LLR_capability_t | Query hardware limits. |

**Action Item:** Please confirm with the SAI vendor if these attributes and counters are supported or planned for the next SDK release.

---

**Doc Status:** Draft v0.4 (Pending Discussion/Supplement)  
**Next Update:** 06/09  
**Maintainer:** Haiyang Zheng (Alibaba)
