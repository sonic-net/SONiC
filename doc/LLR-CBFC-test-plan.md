# LLR & CBFC Test Plan
## References 
1. Ultra Ethernet Specification v1.0.1 section 5.1(LLR) and 5.2(CBFC) https://ultraethernet.org/uec-1-0-spec
2. SAI Proposal: Link Layer Retry (LLR) https://github.com/opencomputeproject/SAI/blob/master/doc/LLR/SAI-Link_Layer_Retry.md
3. SAI Proposal: Credit Based Flow Control https://github.com/opencomputeproject/SAI/blob/master/doc/CBFC/SAI-Credit_Based_Flow_Control.md

## Table of Contents
### Test Topology
1. [Topology 1](#topology-1)
2. [Topology 2](#topology-2)

### LLR testcases
1. [LLR-01](#-llr-01--llr-eligible-frame-sequence-encoding-and-acknolwdgement) LLR-eligible frame sequence encoding and acknolwdgement
2. [LLR-02](#-llr-02--nack-generation-due-to-frame-sequence-gap-detection-and-replay-acceptance) NACK generation due to frame sequence gap detection and replay acceptance
3. [LLR-03](#-llr-03--nack-generation-due-to-bad-crc-frame-reception-and-replay-acceptance) NACK generation due to bad CRC frame reception and replay acceptance
4. [LLR-04](#-llr-04--replay-after-receiving-nack) Replay after receiving NACK
4. [LLR-05](#-llr-05--replay-after-replay-timer-expiry) Replay after replay timer expiry
5. [LLR-06](#-llr-06--poisoned-fcs-handling) Poisoned FCS handling
6. [LLR-07](#-llr-07--outstanding_frames_max-validation) `OUTSTANDING_FRAMES_MAX` validation
7. [LLR-08](#-llr-08--buffer-capacity-validation-when-rtt-is-equivalent-of-500-meter-of-cable) Buffer capacity validation when RTT is equivalent of 500 meter of cable
8. [LLR-09](#-llr-09--recovery-from-flush-state) Recovery from FLUSH state
9. [LLR-10](#-llr-10--latency-of-llr-eligible-traffic-of-different-frame-sizes) Latency of LLR-eligible traffic of different frame sizes
10. [LLR-11](#-llr-11--handling-of-llr-eligible-and-llr-ineligible-frames-in-presence-of-uncorrectable-fec-error) Handling of LLR-eligible and LLR-ineligible frames in presence of uncorrectable FEC error

### CBFC testcases
1. [CBFC-01](#-cbfc-01--credit-handling-by-cbfc-sender) Credit Handling by CBFC Sender
2. [CBFC-02](#-cbfc-02--credit-handling-by-cbfc-receiver) Credit Handling by CBFC Receiver
3. [CBFC-03](#-cbfc-03--lost-credit-recovery-by-cc_updates) Lost credit recovery by CC_Updates
4. [CBFC-04](#-cbfc-04--flow-control-in-presence-of-backpressure) Flow control in presence of backpressure
5. [CBFC-05](#-cbfc-05--vlan-pcp--dei-mapping-to-lossless-vcs) VLAN PCP + DEI mapping to lossless VCs
6. [CBFC-06](#-cbfc-06--ip-dscp-mapping-to-lossless-vcs) IP DSCP mapping to lossless VCs
7. [CBFC-07](#-cbfc-07--ipv6-dscp-mapping-to-lossless-vcs) IPv6 DSCP mapping to lossless VCs
8. [CBFC-08](#-cbfc-08--flow-control-when-per-vc-credit-limits-are-used) Flow control when per-VC credit limits are used
9. [CBFC-09](#-cbfc-09--flow-control-when-totalcredits-limit-is-used) Flow control when `TotalCredits` limit is used
10. [CBFC-10](#-cbfc-10--lossless-traffic-in-3-to-1-incast-scenario) Lossless traffic in 3-to-1 incast scenario
11. [CBFC-11](#-cbfc-11--lossless-and-best-effort-traffic-in-3-to-1-incast-scenario) Lossless and best effort traffic in 3-to-1 incast scenario
12. [CBFC-12](#-cbfc-12--link-bandwidth-utilization-by-lossless-traffic-when-rtt-is-equivalent-of-500-meter-of-cable) Link bandwidth utilization by lossless traffic when RTT is equivalent of 500 meter of cable


## Test Topology
Each of the test cases described in this test plan uses one of the two topologies - <br>

### Topology 1: 
The figure below describes Topology 1, which connects two Tester ports to DUT. This toplogy is used in the most of the test cases defined in this document.

```text
+-----------------+                  +---------------------------------+                  +-----------------+
|                 |                  |              DUT                |                  |                 |
| Tester Port 1   |<---------------->| DUT Port 1           DUT Port 2 |<---------------->| Tester Port 2   |
|                 |      Link 1      |                                 |      Link 2      |                 |
+-----------------+                  +---------------------------------+                  +-----------------+
```

### Topology 2: 
The figure below describes the Topology 2, which connects four Tester ports to DUT. This toplogy is used to test incast scenarios in CBFC.

```text
+-----------------+          +---------------------------------+          +-----------------+
|                 |          |                                 |          |                 |
| Tester Port 1   |<-------->| DUT Port 1                      |          |                 |
|                 |  Link 1  |                                 |          |                 |
+-----------------+          |                                 |          |                 |
                             |                                 |          |                 |
+-----------------+          |                                 |          |                 |
|                 |          |                                 |          |                 |
| Tester Port 2   |<-------->| DUT Port 2          DUT Port 4  |<-------->| Tester Port 4   |
|                 |  Link 2  |               DUT               |  Link 4  |                 |
+-----------------+          |                                 |          |                 |
                             |                                 |          |                 |
+-----------------+          |                                 |          |                 |
|                 |          |                                 |          |                 |
| Tester Port 3   |<-------->| DUT Port 3                      |          |                 |
|                 |  Link 3  |                                 |          |                 |
+-----------------+          |                                 |          |                 |
                             +---------------------------------+          +-----------------+
```
## Test cases
### 🟦 LLR-01 • LLR-eligible frame sequence encoding and acknolwdgement
#### Objective
Verify LLR Tx correctly encodes sequence number for LLR-eligible frames, LLR Rx correctly generate ACK for continuous sequence.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate.
3. Verify that DUT receives 1000 LLR-eligible frames on port 1 and transmits 1000 frames as LLR-eligible frames on port 2
   - DUT Port 1 `LLR_RX_OK` = Tester Port 1 `LLR_TX_OK` = 1000
   - DUT Port 2 `LLR_TX_OK` = Tester Port 2 `LLR_RX_OK` = 1000.
4. Verify that DUT Port 1 send periodic ACK and DUT Port 2 receive and count receiving ACK
   - DUT Port 1 `LLR_TX_ACK_CTL_OS` & Tester Port 1 `LLR_RX_ACK_CTL_OS` > 0
   - DUT Port 2 `LLR_RX_ACK_CTL_OS` & Tester Port 2 `LLR_TX_ACK_CTL_OS` > 0
5. Verify no NACK is generated. 
   - DUT Port 1 `LLR_TX_NACK_CTL_OS` = Tester Port 1 `LLR_RX_NACK_CTL_OS` = 0
   - DUT Port 2 `LLR_RX_NACK_CTL_OS` = Tester port 2 `LLR_TX_NACK_CTL_OS` = 0
6. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-02 • NACK generation due to frame sequence gap detection and replay acceptance
#### Objective
Verify that DUT (a)generates NACK when it detects sequence gap, and (b)accepts subsequent replay
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Configure `init_seq` = 1 on Tester Port 1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2
2. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate, simulating sequence jump by 1 from 901st frame (eg. ...900, 902, 903,...).
3. Verify DUT send 1 NACK with sequence number 900, and Tester triggered one replay event 
   - `LLR_TX_NACK_CTL_OS` on DUT Port 1 = `LLR_RX_NACK_CTL_OS` on Tester Port 1 = 1
   - Sequence number in NACK is 900 
   - `LLR_RX_REPLAY` on DUT Port 1 = `LLR_TX_REPLAY` on Tester Port 1
4. Verify LLR Rx Expected Seq good on DUT Port 1 and LLR Tx Replayed Frames on Tester port 1
   - `LLR_RX_EXPECTED_SEQ_GOOD` on DUT Port 1 = 1000
   - LLR Tx Replayed Frames on Tester Port 1 > 0  
5. Verify LLR Tx and Rx state after replay
   - `LLR_TX_STATUS` on Tester Port 1 & DUT Port 2 = `SAI_PORT_LLR_TX_STATUS_ADVANCE`
   - `LLR_RX_STATUS` on DUT Port 1 & Tester Port 2 = `SAI_PORT_LLR_RX_STATUS_SEND_ACKS`
6. Verify there is no frame loss in tester traffic statistics
7. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-03 • NACK generation due to bad CRC frame reception and replay acceptance
#### Objective
Verify that DUT (a)generates NACK when it recieves bad CRC frame, and (b)accepts subsequent replay
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Configure `init_seq` = 1 on Tester Port 1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate while injecting bad CRC at 901st frame.
3. Verify DUT send 1 NACK with sequence number 900, and Tester triggered one replay event 
   - `LLR_TX_NACK_CTL_OS` on DUT Port 1 = `LLR_RX_NACK_CTL_OS` on Tester Port 1 = 1
   - Sequence number in NACK is 900
4. Verify LLR Rx Expected Seq Good, Rx Expected Seq Bad on DUT Port 1 and LLR Tx Replayed Frames on Tester port 1
   - `LLR_RX_EXPECTED_SEQ_GOOD` on DUT Port 1 = 1000
   - `LLR_RX_EXPECTED_SEQ_BAD` on DUT Port 1 = 1000
   - LLR Tx Replayed Frames on Tester Port 1 > 0  
5. Verify LLR Tx and Rx state after replay
   - `LLR_TX_STATUS` on Tester Port 1 & DUT Port 2 = `SAI_PORT_LLR_TX_STATUS_ADVANCE`
   - `LLR_RX_STATUS` on DUT Port 1 & Tester Port 2 = `SAI_PORT_LLR_RX_STATUS_SEND_ACKS`
6. Verify there is no frame loss in tester traffic statistics
7. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-04 • Replay after receiving NACK
#### Objective
Verify that DUT replays frames from its replay buffer after receiving NACK
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate and simulate frame drop at sequence 901 on reception in Tester Port 2.
3. Verify DUT Port 2 receives a NACK from Tester Port 2 and does a replay
   - `LLR_RX_NACK_CTL_OS` on DUT Port 2 = `LLR_TX_NACK_CTL_OS` on Tester Port 2 = 1
   - `LLR_TX_REPLAY` on DUT Port 2 = `LLR_RX_REPLAY` on Tester Port 2 = 1
4. Verify DUT Port 2 ends up sending more than 1000 LLR-eligble frames to Tester Port 2
   - `LLR_TX_OK` on DUT Port 2 > 1000
5. Verify LLR Tx and Rx state after replay
   - `LLR_TX_STATUS` on DUT Port 2 = `SAI_PORT_LLR_TX_STATUS_ADVANCE`
   - `LLR_RX_STATUS` on Tester Port 2 = `SAI_PORT_LLR_RX_STATUS_SEND_ACKS`
6. Verify there is no frame loss in tester traffic statistics
7. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-05 • Replay after replay timer expiry
#### Objective
Verify that DUT replays frames from its replay buffer after replay timer expiry
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2. Configure `REPLAY_COUNT_MAX` = 3, `RE_INIT_ON_FLUSH` = FALSE in DUT. 
2. Pause ACK Tx from Tester Port 2.
3. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate. 
4. Verify DUT replays all 1000 frames three times so that total transmitted LLR Frames are 4000.
   - DUT Port 2 `LLR_TX_OK` = Tester Port 2 `LLR_RX_OK` = 4000.
   - DUT Port 2 `LLR_TX_REPLAY` = 3
5. Verify that DUT Port 2 is in FLUSH state after replay
   - `LLR_TX_STATUS` on DUT Port 2 = `SAI_PORT_LLR_TX_STATUS_FLUSH`
6. Repeat the steps for maximum frame size supported by DUT.
7. Repeat the above steps by replacing step 2 with freezing ACK sequence instead of blocking ACK Tx from Tester Port 2.
---

### 🟦 LLR-06 • Poisoned FCS handling
#### Objective
Verify that DUT does not send NACK when frames with poisoned FCS are received.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. Send 1000 64B LLR-eligible frames with poisoned FCS from Tester Port 1 at 100% line rate. 
3. Verify that DUT Port 1 correctly identifies frames with poisoned FCS.
   - DUT Port 1 `LLR_RX_POISONED` = 1000
4. Verify no NACK is sent by DUT Port 1
   - Tester Port 1 `LLR_RX_NACK_CTL_OS` = 0
5. Verify there is no replay on any port
   - `LLR_TX_REPLAY` and `LLR_RX_REPLAY` on all DUT and Tester ports = 0
5. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-07 • `OUTSTANDING_FRAMES_MAX` validation
#### Objective
Verify that DUT obeys configured `OUTSTANDING_FRAMES_MAX` 
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Configure following in DUT Port 2 
   - `OUTSTANDING_FRAMES_MAX` = 10 
   - `OUTSTANDING_BYTES_MAX` > 10 * maximum frame size supported by DUT
   - `REPLAY_COUNT_MAX` = 3, 
   - `FLUSH_LLR_FRAME_ACTION` = `SAI_LLR_FRAME_ACTION_BLOCK` or `SAI_LLR_FRAME_ACTION_DISCARD`,
   - `RE_INIT_ON_FLUSH` = FALSE,  
2. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
3. Pause ACK Tx from Tester Port 2.
4. Send 1000 64B LLR-eligible frames from Tester Port 1 at 100% line rate. 
5. Verify that DUT Port 2 does not send more than 10 frames in each replay attempt
   - DUT Port 2 `LLR_TX_REPLAY` = 3
   - Tester Port 2 `LLR_RX_OK` = 40
   - Tester Port 2 `LLR_RX_DUPLICATE_SEQ` = 30
6. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟦 LLR-08 • Buffer capacity validation when RTT is equivalent of 500 meter of cable
#### Objective
Verify that DUT can support reach of 500 meter cable (approximate RTT = 5 us)
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Measure L, the length of Link 2, in meter. On Tester Port 2, simulate additional RTT delay for (500-L) meter cable by using the formula *2 × 5 × (500-L)* ns.
2. On DUT Port 2, configure `OUTSTANDING_FRAMES_MAX`, `OUTSTANDING_BYTES_MAX`, `REPLAY_TIMER_MAX` appropriately to support 500 meter cable reach.
3. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
4. Send LLR-eligible 64B frames traffic at 100% line rate from Tester Port 1 for 5 minutes.
5. Verify that `LLR_TX_OK` on Tx ports match with `LLR_RX_OK` on Rx ports.
   - Tester Port 1 `LLR_TX_OK` = DUT Port 1 `LLR_RX_OK`
   - DUT Port 2 `LLR_TX_OK` = Tester Port 2 `LLR_RX_OK`
6. Verify that there is no replay from DUT Port 2
   - DUT Port 2 `LLR_TX_REPLAY` = Tester Port 2 `LLR_RX_REPLAY` = 0
7. Verify that recieved traffic L1 line rate (account for frame, preamble and IPG but not ACK CtlOS) at Tester Port 2 > 99%
8. Verify there is no frame loss in tester traffic statistics
---

### 🟦 LLR-09 • Recovery from FLUSH state
#### Objective
Verify that DUT can recover from FLUSH state when `RE_INIT_ON_FLUSH` is enabled
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. On DUT Port 2, configure `FLUSH_LLR_FRAME_ACTION` = `SAI_LLR_FRAME_ACTION_DISCARD`, `RE_INIT_ON_FLUSH` = true, `REPLAY_COUNT_MAX` = 3.
2. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
3. Pause ACK Tx from Tester Port 2.
4. Clear `LLR_RX_INIT_CTL_OS`, `LLR_TX_INIT_ECHO_CTL_OS`counters on Tester Port 2. 
5. Send 100 64B LLR-eligible frames from Tester Port 1 at 100% line rate.
6. Wait at least 30 seconds and then verify that DUT replayed frames due to replay timer expiry and then re-initilaized LLR
   - Tester Port 2 `LLR_RX_OK` = 400
   - Tester Port 2 `LLR_RX_EXPECTED_SEQ_GOOD` = 100
   - Tester Port 2 `LLR_RX_DUPLICATE_SEQ` = 300
   - Tester Port 2  `LLR_RX_INIT_CTL_OS` > 0 
   - Tester Port 2  `LLR_TX_INIT_ECHO_CTL_OS` > 0
7. Resume ACK Tx from Tester Port 2.
8. Clear `LLR_RX_OK`, `LLR_RX_EXPECTED_SEQ_GOOD` in Tester Port 2.
9. Send 100 64B LLR-eligible frames from Tester Port 1 at 100% line rate.
10. Verify that DUT Port 2 can successfully sends LLR-eligible frame 
   - Tester Port 2 `LLR_RX_OK` = 100
   - Tester Port 2 `LLR_RX_EXPECTED_SEQ_GOOD` = 100
---

### 🟦 LLR-10 • Latency of LLR-eligible traffic of different frame sizes
#### Objective
Verify that latency for LLR-eligible traffic is consistent across different frame sizes.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. From Tester Port 1 send LLR-eligible traffic for 2 minutes for each frame size from the following list - 64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,*max frame size*+x bytes where x is 0, +1 or -1 (except for 64B frames, x=+1 only and for *max frame size* x=-1 only).
3. In each iteration, verify there is no frame loss in tester traffic statistics
4. In each iteration verify end-to-end count of LLR-eligible frames matches
   - Tester Port 1 `LLR_TX_OK` = Tester Port 2 `LLR_RX_OK`
5. In each iteration, verify latency of traffic reported in tester traffic statistics is consistent with cut-through/store-and-forward opeation mode of DUT.
---

### 🟦 LLR-11 • Handling of LLR-eligible and LLR-ineligible frames in presence of uncorrectable FEC error
#### Objective
Verify that in presence of uncorrectable FEC error there is no loss in LLR-eligible frames. 
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable LLR on Tester Port 1, 2 and DUT Port 1, 2.
2. From Tester Port 1 inject FEC error in such a way that there are uncorrectable codewords injected periodically, but does not cause link failure.
3. From Tester Port 1 send LLR-eligible 64B frames and LLR-ineligible 64B frames each at 50% line rate for two minutes simultaneously.
4. Verify that DUT generates NACKs as a result of dropped or corrupted frames reception due to uncorrectable FEC errors. 
   - Tester Port 1 `LLR_RX_NACK_CTL_OS` > 0
5. From tester traffic statistics verify that while LLR-ineligible traffic sufffers some frame loss, there is no frame loss reported LLR-eligible traffic.
6. Repeat the above steps for maximum frame size supported by DUT.
---

### 🟪 CBFC-01 • Credit Handling by CBFC Sender
#### Objective
Verify that DUT as CBFC Sender uitlizes credit correctly
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on DUT Port 2 and Tester Port 2. Configure a lossless VC,`VC[0]`, in CBFC Sender of DUT Port 2 and CBFC Receiver of Tester Port 2. Map `VC[0]` to same value of `mac.vlan.pcp_dei` or `ip.dscp` on Sender and Receiver. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` in CBFC Sender and CBFC Receiver.
2. Send one million packet having same `mac.vlan.pcp_dei`/`ip.dscp` as set in Sender/Receiver VC[0] mapping from Tester Port 1 for each of the following frame sizes at 100% line rate - 
   <br>64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,*max frame size*+x bytes where x is 0, +1 or -1 (except for 64B frames, x=+1 only and for *max frame size* x=-1 only).
3. After each iteration of frame size verify that no frame loss is reported from tester traffic statistics.
4. After each iteration of frame size verify that value of `S_VC_CC[0]` in DUT Port 2 Sender is correct - 
   - Record `S_VC_CC[0]` in DUT Port 2 Sender (by either directly reading counter from DUT Port 2 or from packet capture of CC_Updates sent from DUT Port 2).
   <br>DUT Port 2  ***S_VC_CC[0] = (S_VC_CC[0] recorded in previous step + Total_Credits_Consumed) mod 2^20*** where Total_Credits_Consumed (credits consumed by the packets in this iteration of frame size) is calculated using the formula ***Total_Credits_Consumed = roundup((frame size + PktOvhd) ÷ CreditSize)x1,000,000***
   - DUT Port 2 `S_VC_CC[0]` = Tester Port 2 `R_VC_CC[0]` = Tester Port 2 `R_VC_CF[0]`
---

### 🟪 CBFC-02 • Credit Handling by CBFC Receiver
#### Objective
Verify that DUT as CBFC Receiver uitlizes credit correctly
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1 and DUT Port 1. Configure a lossless VC,`VC[0]`, in CBFC Sender of Tester Port 1 and CBFC Receiver of DUT Port 1. Map `VC[0]` to same value of `mac.vlan.pcp_dei` or `ip.dscp` on Sender and Receiver. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` in CBFC Sender and CBFC Receiver.
2. Stop sending CC_Updates from Tester Port 1.
3. Send one million packet having same `mac.vlan.pcp_dei`/`ip.dscp` as set in Sender/Receiver VC[0] mapping from Tester Port 1 for each of the following frame sizes at 100% line rate - 
   <br>64+x,128+x,256+x,512+x,1518+x,2048+x,4096+x,*max frame size*+x bytes where x is 0, +1 or -1 (except for 64B frames, x=+1 only and for *max frame size* x=-1 only).
4. After each iteration of frame size verify that no frame loss is reported from tester traffic statistics.
5. After each iteration of frame size verify that CC and CF counter matches on Tester Port 2
   - Tester Port 2 `S_VC_CC[0]` = Tester Port 2 `S_VC_CF[0]` 
---

### 🟪 CBFC-03 • Lost credit recovery by CC_Updates
#### Objective
Verify that DUT can recover lost credits from CC_Updates.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1 and DUT Port 1. Configure a lossless VC,`VC[0]`, in CBFC Sender of Tester Port 1 and CBFC Receiver of DUT Port 1. Map `VC[0]` to same value of `mac.vlan.pcp_dei` or `ip.dscp` on Sender and Receiver. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` in CBFC Sender and CBFC Receiver.
2. Stop sending CC_Updates from Tester Port 1.
3. Send 100 1518B packets having same `mac.vlan.pcp_dei`/`ip.dscp` as set in Sender/Receiver `VC[0]` mapping from Tester Port 1 with corrupted FCS.
4. Verify that DUT Port 1 Receiver does not free up credits for corrupted packets.
   - Tester Port 1 `S_VC_CC[0]` > 0
   - Tester Port 1 `S_VC_CF[0]` = 0
5. Resume sending CC_Updates from Tester Port 1. 
6. Verify that DUT Port 1 Receiver reconcile credits after receiving CC_Updates and free up credits.
   - Tester Port 1 `S_VC_CC[0]` > 0
   - Tester Port 1 `S_VC_CF[0]` = Tester Port 1 `S_VC_CC[0]`
---

### 🟪 CBFC-04 • Flow control in presence of backpressure
#### Objective
Verify that DUT exhibits flow control in presence of backpressure.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure a lossless VC,`VC[0]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to same value of `mac.vlan.pcp_dei` or `ip.dscp` on Sender and Receiver. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. Send a continuous traffic stream of 64B packets having same `mac.vlan.pcp_dei`/`ip.dscp` as set in Sender/Receiver VC[0] mapping from Tester Port 1 at 100% line rate.
3. Verify that there is no backpressure on traffic throughput
   - Tester Port 1 L1 Tx line rate => 99%
   - Tester Port 2 L1 Rx line rate => 99%
4. Create backpreussure from Tester Port 2 in such a way that rate of returned credits would exert flow control and allow traffic only up to 50% line rate.
5. Verify that traffic throughput is reduced. 
   - Tester Port 1 L1 Tx line rate ~ 50%
   - Tester Port 2 L1 Rx line rate ~ 50%
6. Increase backpreussure from Tester Port 2 further so that it stops freeing up credits altogether.
7. Verify line rate utilization almost falls to zero (there will be some utilization due to CC_Updates)
   - Tester Port 1 L1 Tx line rate ~ 0%
   - Tester Port 2 L1 Rx line rate ~ 0%
8. Remove backpressure from Tester Port 2.
9. Verify that traffic throughput has gone back to nearly full utilisation
   - Tester Port 1 L1 Tx line rate => 99%
   - Tester Port 2 L1 Rx line rate => 99%
10. Stop traffic stream and verify that there is no frame loss from tester traffic statistics.
11. Repeat steps 2-10 for each frame size from the following list - <br>
   65, 128+x, 256+x, 512+x, 1518+x, 2048+x, 4096+x, *max frame size*+x bytes where x is 0, +1 or -1 (except for *max frame size* x=-1 only).
---

### 🟪 CBFC-05 • VLAN PCP + DEI mapping to lossless VCs
#### Objective
Verify that VLAN PCP + DEI mapping to lossless VCs works in DUT
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure two lossless VCs,`VC[0]` and `VC[1]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to VLAN PCP = 0, DEI = 0 and `VC[1]` to VLAN PCP = 7, DEI = 1. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. Stop sending CC_Updates from Tester Port 1.
3. Stop receiving CC_Updates on Tester Port 2. 
4. Verify all VC credit counters are zero in Tester Port 1,2
   - Tester Port 1 `S_VC_CC[0]`, `S_VC_CC[1]`, `S_VC_CF[0]`, `S_VC_CF[1]` = 0
   - Tester Port 2 `R_VC_CC[0]`, `R_VC_CC[1]`, `R_VC_CF[0]`, `R_VC_CF[1]` = 0
5. Send 100 64B packets with VLAN PCP = 0, DEI = 0 from Tester Port 1 at 100% line rate.
6. Verify that `VC[0]` credit counters have increased and match, but `VC[1]` counters stay zero.
   - Tester Port 1 `S_VC_CC[0]` = Tester Port 1 `S_VC_CF[0]` = Tester Port 2 `R_VC_CC[0]` = Tester Port 2 `R_VC_CF[0]`
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` > 0
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` = 0
7. Send 100 64B packets with VLAN PCP = 7, DEI = 1 from Tester Port 1 at 100% line rate.
8. Verify that now `VC[1]` counters are updated and match.
   - Tester Port 1 `S_VC_CC[1]` = Tester Port 1 `S_VC_CF[1]` = Tester Port 2 `R_VC_CC[1]` = Tester Port 2 `R_VC_CF[1]`
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` > 0
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` do not change from step 6.
---

### 🟪 CBFC-06 • IP DSCP mapping to lossless VCs
#### Objective
Verify that IP DSCP mapping to lossless VCs works in DUT
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure two lossless VCs,`VC[0]` and `VC[1]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to IP DSPCP = 0 and `VC[1]` to IP DSCP = 63. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. Stop sending CC_Updates from Tester Port 1.
3. Stop receiving CC_Updates on Tester Port 2. 
4. Verify all VC credit counters are zero in Tester Port 1,2
   - Tester Port 1 `S_VC_CC[0]`, `S_VC_CC[1]`, `S_VC_CF[0]`, `S_VC_CF[1]` = 0
   - Tester Port 2 `R_VC_CC[0]`, `R_VC_CC[1]`, `R_VC_CF[0]`, `R_VC_CF[1]` = 0
5. Send 100 64B packets with IP DSCP = 0 from Tester Port 1 at 100% line rate.
6. Verify that `VC[0]` credit counters have increased and match, but `VC[1]` counters stay zero.
   - Tester Port 1 `S_VC_CC[0]` = Tester Port 1 `S_VC_CF[0]` = Tester Port 2 `R_VC_CC[0]` = Tester Port 2 `R_VC_CF[0]`
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` > 0
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` = 0
7. Send 100 64B packets with IP DSCP = 63 from Tester Port 1 at 100% line rate.
8. Verify that now `VC[1]` counters are updated and match.
   - Tester Port 1 `S_VC_CC[1]` = Tester Port 1 `S_VC_CF[1]` = Tester Port 2 `R_VC_CC[1]` = Tester Port 2 `R_VC_CF[1]`
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` > 0
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` do not change from step 6.
---

### 🟪 CBFC-07 • IPv6 DSCP mapping to lossless VCs
#### Objective
Verify that IPv6 DSCP mapping to lossless VCs works in DUT
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure two lossless VCs,`VC[0]` and `VC[1]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to IPv6 DSPCP = 0 and `VC[1]` to IPv6 DSCP = 63. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]`, `VC_CreditLimit[1]` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. Stop sending CC_Updates from Tester Port 1.
3. Stop receiving CC_Updates on Tester Port 2. 
4. Verify all VC credit counters are zero in Tester Port 1,2
   - Tester Port 1 `S_VC_CC[0]`, `S_VC_CC[1]`, `S_VC_CF[0]`, `S_VC_CF[1]` = 0
   - Tester Port 2 `R_VC_CC[0]`, `R_VC_CC[1]`, `R_VC_CF[0]`, `R_VC_CF[1]` = 0
5. Send 100 64B packets with IPv6 DSCP = 0 from Tester Port 1 at 100% line rate.
6. Verify that `VC[0]` credit counters have increased and match, but `VC[1]` counters stay zero.
   - Tester Port 1 `S_VC_CC[0]` = Tester Port 1 `S_VC_CF[0]` = Tester Port 2 `R_VC_CC[0]` = Tester Port 2 `R_VC_CF[0]`
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` > 0
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` = 0
7. Send 100 64B packets with IPv6 DSCP = 63 from Tester Port 1 at 100% line rate.
8. Verify that now `VC[1]` counters are updated and match.
   - Tester Port 1 `S_VC_CC[1]` = Tester Port 1 `S_VC_CF[1]` = Tester Port 2 `R_VC_CC[1]` = Tester Port 2 `R_VC_CF[1]`
   - Tester Port 1 `S_VC_CC[1]`, Tester Port 1 `S_VC_CF[1]`, Tester Port 2 `R_VC_CC[1]`, Tester Port 2 `R_VC_CF[1]` > 0
   - Tester Port 1 `S_VC_CC[0]`, Tester Port 1 `S_VC_CF[0]`, Tester Port 2 `R_VC_CC[0]`, Tester Port 2 `R_VC_CF[0]` do not change from step 6.
---

### 🟪 CBFC-08 • Flow control when per-VC credit limits are used
#### Objective
Verify that per-vc credit limits work correctly in DUT.
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure four lossless VCs,`VC[0]`,`VC[1]`,`VC[2]`,`VC[3]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to IP DSCP = 0, `VC[1]` to IP DSCP = 7, `VC[2]` to IP DSCP = 15, `VC[3]` to IP DSCP = 31. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` in CBFC Sender and CBFC Receiver ( x = 0,1,2,3).<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. From Tester Port 1 send 4 traffic streams of 1518B frame size with IP DSCP values 0,7,15,31 each at 25% line rate.
3. From tester traffic statistics verify that tx and rx rate of traffic in each vc is ~25% of line rate.
4. Create backpreussure from Tester Port 2 in such a way that rate of returned credits would exert flow control and allow VC[1] traffic only up to 10% line rate.
5. From tester traffic statistics verify that 
   - tx and rx rate of traffic in `VC[0]`,`VC[2]`,`VC[3]` is ~25% of line rate 
   - tx and rx rate of traffic in `VC[1]` is ~10% of line rate 
6. Increase backpreussure from Tester Port 2 in such a way that it stops freeing up credits for VC[1] altogether.
7. From tester traffic statistics verify that 
   - tx and rx rate of traffic in `VC[0]`,`VC[2]`,`VC[3]` is ~25% of line rate 
   - tx and rx rate of traffic in `VC[1]` is 0% of line rate
8. Remove backpreussure from Tester Port 2 for VC[1].
9. From tester traffic statistics verify that tx and rx rate of traffic in each vc is ~25% of line rate again.
10. Stop all traffic. Verify that there is no frame loss from tester traffic statistics.
---

### 🟪 CBFC-09 • Flow control when `TotalCredits` limit is used
#### Objective
Verify that `TotalCredits` limit for all lossless VCs work correctly in DUT
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure two lossless VCs,`VC[0]`,`VC[1]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to IP DSCP = 0 and `VC[1]` to IP DSCP = 31. Also, set same `CreditSize`, `PktOvhd`, `TotalCredits` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `TotalCredits` values configured in Tester Port 1,DUT Port 1 need not be same as those in DUT Port 2,Tester Port 2.
2. From Tester Port 1 send 2 traffic streams of 1518B frame size with IP DSCP values 0,31 each at 50% line rate.
3. From tester traffic statistics verify that tx and rx rate of traffic in each vc is ~50% of line rate.
4. Create backpreussure from Tester Port 2 in such a way that returned credits would exert flow control and allow VC[1] traffic only up to 30% line rate.
5. From tester traffic statistics verify that tx and rx rate of traffic in each vc is reduced, but must not be zero.
6. Increase backpreussure from Tester Port 2 in such a way that it stops freeing up credits for VC[1] altogether.
7. From tester traffic statistics verify that tx and rx rate of traffic in each vc is ~0% of line rate.
8. Remove backpreussure from Tester Port 2 for VC[1].
9. From tester traffic statistics verify that tx and rx rate of traffic in each vc is ~50% of line rate again.
10. Stop all traffic. Verify that there is no frame loss from tester traffic statistics.
---

### 🟪 CBFC-10 • Lossless traffic in 3-to-1 incast scenario
#### Objective
Verify DUT operation for lossless traffic in incast scenario when congestion builds up and then clears.
#### Topology
This test case uses [Topology 2](#topology-2)
#### Steps
1. Enable CBFC on Tester Port 1,2,3,4 and DUT Port 1,2,3,4. Configure one lossless VC in CBFC Sender of Tester Port 1,2,3, DUT Port 4 and CBFC Receiver of DUT Port 1,2,3, Tester Port 4. Map lossless VC to IP DSCP = 0. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` values configured need not be same between diferent Tester, DUT port pairs.
2. From Tester Port 1 send a traffic stream of 1518B frame size with IP DSCP = 0 at 100% line rate.
3. Verify that 
   - Tester Port 1 tx line rate => 99%
   - Tester Port 4 rx line rate => 99%
4. From Tester Port 2 send a traffic stream of 1518B frame size with IP DSCP = 0 at 100% line rate.
5. Verify that 
   - Tester Port 1 tx line rate ~50% 
   - Tester Port 2 tx line rate ~50% 
   - Tester Port 4 rx line rate => 99%
6. From Tester Port 3 send a traffic stream of 1518B frame size with IP DSCP = 0 at 100% line rate.
7. Verify that 
   - Tester Port 1 tx line rate ~33% 
   - Tester Port 2 tx line rate ~33% 
   - Tester Port 2 tx line rate ~33% 
   - Tester Port 4 rx line rate => 99%
8. Stop traffic from Tester Port 2,3.
9. Verify that 
   - Tester Port 1 tx line rate => 99% 
   - Tester Port 4 rx line rate => 99%
10. Stop traffic from Tester Port 1. Verify that there is no frame loss from tester traffic statistics considering all flows from Tester Port 1,2,3.
---

### 🟪 CBFC-11 • Lossless and best effort traffic in 3-to-1 incast scenario
#### Objective
Verify DUT operation in incast scenario in presence of lossless and best effort traffic.
#### Topology
This test case uses [Topology 2](#topology-2)
#### Steps
1. Enable CBFC on Tester Port 1,2,3,4 and DUT Port 1,2,3,4. Configure one lossless VC and one best effort VC in CBFC Sender of Tester Port 1,2,3, DUT Port 4 and CBFC Receiver of DUT Port 1,2,3, Tester Port 4. Map lossless VC to IP DSCP = 0 and best effort VC to IP DSCP = 4. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` in CBFC Sender and CBFC Receiver.<br>
*Note*: `CreditSize`, `PktOvhd`, `VC_CreditLimit[x]` values configured need not be same between diferent Tester, DUT port pairs.
2. From Tester Port 1,2,3 send 2 traffic streams of 1518B frame size with IP DSCP values 0,4 each at 50% line rate.
3. Verify that 
   - Tester Port 1 tx line rate ~33% 
   - Tester Port 2 tx line rate ~33% 
   - Tester Port 2 tx line rate ~33% 
   - Tester Port 4 rx line rate => 99%
4. Stop Traffic. From tester traffic statistics verify that there is no loss reported for traffic in lossless VC whereas there must be some loss for traffic in best effort VC.
---

### 🟪 CBFC-12 • Link bandwidth utilization by lossless traffic when RTT is equivalent of 500 meter of cable
#### Objective
Verify DUT can uitlize maximum link bandwidth when Sender and Receiver are 500m apart
#### Topology
This test case uses [Topology 1](#topology-1)
#### Steps
1. Enable CBFC on Tester Port 1,2 and DUT Port 1,2. Configure a lossless VC,`VC[0]`, in CBFC Sender of Tester Port 1, DUT Port 2 and CBFC Receiver of DUT Port 1, Tester Port 2. Map `VC[0]` to IP DSCP = 0 on Sender and Receiver.
2. Configure `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` of DUT Port 2 in such way that it takes 500m of cable delay into account. Also, set same `CreditSize`, `PktOvhd`, `VC_CreditLimit[0]` in Tester Port 2.
3. Measure L, the length of Link 2, in meter. On Tester Port 2, simulate additional RTT delay of (500-L) meter by using the formula *2 × 5 × (500-L) ns*
4. From Tester Port 1 send a traffic stream of 64B frame size with IP DSCP = 0 at 100% line rate for a minute.
5. Verify that 
   - Tester Port 1 tx line rate  => 33% 
   - Tester Port 2 rx line rate => 99%
6. Stop traffic. Verify that there is no frame loss reported from tester traffic statistics.
7. Repeat steps 4-6 for maximum frame size supported by DUT.