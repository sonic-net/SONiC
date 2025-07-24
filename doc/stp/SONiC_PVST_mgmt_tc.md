# SonicMgmt Testcases for PVST
#### Rev 1.0

# Table of Contents
  * [List of Tables](#list-of-tables)
  * [Revision](#revision)
  * [About this Manual](#about-this-manual)
  * [Scope](#scope)
  * [Testing Strategy for PVST feature](#testing-strategy-for-pvst-feature)
  * [Test cases](#test-cases)
    * [TC1: Validate SONIC DUT acting as root bridge](#tc_1-validate-sonic-dut-acting-as-root-bridge)
    * [TC2: Validate SONIC DUT as designated bridge](#tc_2-validate-sonic-dut-as-designated-bridge)
    * [TC3: Validate shutting down the root port on SONIC DUT](#tc_3-validate-shutting-down-the-root-port-on-sonic-dut)
    * [TC4: Validate bridge priority configuration on SONIC DUT](#tc_4-validate-bridge-priority-configuration-on-sonic-dut)
    * [TC5: Validate port priority change in BPDU](#tc_5-validate-port-priority-change-in-bpdu)
    * [TC6: Validate port cost change in BPDU](#tc_6-validate-port-cost-change-in-bpdu)
    * [TC7: Validate root guard functionality on SONIC DUT](#tc_7-validate-root-guard-functionality-on-sonic-dut)
    * [TC8: Validate BPDU guard functionality on SONIC DUT](#tc_8-validate-bpdu-guard-functionality-on-sonic-dut)
    * [TC9: Validate PVST timer configurations](#tc_9-validate-pvst-timer-configurations)
    * [TC10: Validate Backup port functionality](#tc_10-validate-backup-port-functionality)
    * [TC11: Validate Mac flush functionality](#tc_11-validate-mac-flush-functionality)
  * [References](#references)
  * [Abbreviations](#abbreviations)
  * [List of Tables](#list-of-tables)


# List of Tables
[Table 1: Abbreviations](#table-1-abbreviations)

# Revision
| Rev |     Date    |       Author               | Change Description                |
|:---:|:-----------:|:--------------------------:|-----------------------------------|
| 0.1 | 24/07/2025  |     Venkata Gouri Rajesh E, Praveen Hoskote Madhusudana       | Initial version                   |

# About this Manual
This document describes the approach that can be taken for adding support for PVST feature testing as part of sonic-mgmt test suite.
# Scope
This document describes the high level details of SONiC management test-cases for PVST feature.


# Testing Strategy for PVST feature:
Existing t0 topology will be used for developing the PVST test suite. A simplified version of the topology will be as shown above where the SONIC DUT ports will be connected to PTF.
Following mechanisms will be used in the test script implementation 

- SONIC DUT will be configured using the available CLICK CLIs for PVST
- Verification of operational data will be performed by fetching the data from the redis DB (like spanning tree port states, root port, root bridge etc)
- PTF will be used to validate the BPDUs received from SONIC DUT. For example, based on any configuration change on SONIC DUT whether the information is reflected in the BPDUs (Ex - bridge priority, timer value etc).
- PTF will be used to generate the BPDUs as well. For example, to simulate a peer device acting as root bridge, PTF will generate BPDUs with better bridge priority than the DUT bridge priority. Packets need to be generated periodically from PTF to simulate the expected protocol behaviour.

# Test cases:
The test cases here are to validate the basic functionality of PVST feature.

## TC1: Validate SONIC DUT acting as root bridge
1)	Enable PVST in global mode on SONIC DUT. This will enable PVST on the already configured VLAN 1000.
2)	SONIC DUT should start transmitting the BPDUs after enabling PVST. Verify SONIC DUT is acting as the root bridge by checking the root bridge id in APP DB.
3)	Verify the port state transitions on SONIC DUT from listening -> learning -> forwarding
4)	On PTF capture the BPDUs on Ethernet4 and Ethernet8, validate with the expected BPDU packet.
5)	From PTF, send L2 data packets from Ethernet4 on VLAN 1000 and verify it’s received back on Ethernet8

## TC2: Validate SONIC DUT as designated bridge
1)	From PTF send packets with better bridge priority than SONIC DUT from all the ports
2)	Verify on SONIC DUT the root bridge is selected with root bridge id sent in the BPDU from PTF
3)	Verify on SONIC DUT the root port is selected, and root port is in forwarding state by fetching the information from STP_VLAN_TABLE and STP_VLAN_PORT_TABLE entries from APP DB
4)	Verify on SONIC DUT port Ethernet8 is in blocking state
5)	From PTF send L2 data packets from Ethernet4 for VLAN 1000 and verify it’s not received back on Ethernet8 as the port is in blocking state
6)	Verify the source MAC of the packet sent is learnt on Etherent4 for VLAN 1000 on SONIC DUT
7)	From PTF send L2 data packets from Ethernet8 for VLAN 1000 and verify it’s not received back on Ethernet4 as Ethernet8 is in blocking state
8)	Verify the source MAC of the packet sent is not learnt on Ethernet8 for VLAN 100 on SONIC DUT as port is in blocking state


## TC3: Validate shutting down the root port on SONIC DUT
1)	From PTF send packets with better bridge priority than SONIC DUT from all the ports
2)	Verify on SONIC DUT port Ethernet4 is in forwarding state and Ethernet8 is in blocking state
3)	Shutdown the Ethernet4 port and verify Ethernet8 moves to forwarding state on SONIC DUT
4)	Enable (startup) the port Ethernet4 and verify Ethernet4 moves to forwarding state and Ethernet8 moves to blocking state again.

## TC4: Validate bridge priority configuration on SONIC DUT
1)	From PTF send packets with better bridge priority than SONIC DUT from all the ports
2)	Verify on SONIC DUT the root bridge is selected with root bridge id sent in the BPDU from PTF
3)	Modify the bridge priority on SONIC DUT so that it has better bridge priority than PTF generated packets
4)	Verify on SONIC DUT the root bridge is selected as self, and all ports are in forwarding state 
5)	On PTF capture the packets generated on Ethernet interfaces and verify the root bridge id is same as SONIC DUT

## TC5: Validate port priority change in BPDU
1)	From PTF send packets with better bridge priority than SONIC DUT from all the ports
2)	Verify on SONIC DUT the root bridge is selected with root bridge id sent in the BPDU from PTF
3)	Verify on SONIC DUT the root port is selected, and root port is in forwarding state by fetching the information from STP_VLAN_TABLE and STP_VLAN_PORT_TABLE entries from APP DB
4)	Verify on SONIC DUT port Ethernet8 is in blocking state
5)	From PTF, send a BPDU with better port priority to Ethernet8 port of SONIC DUT
6)	Verify on SONIC DUT port Ethernet8 becomes root port and moves to forwarding state and Ethernet4 moves to blocking state.

## TC6: Validate port cost change in BPDU
1)	From PTF send packets with better bridge priority than SONIC DUT to Ethernet4
2)	Verify on SONIC DUT the root bridge is selected with root bridge id sent in the BPDU from PTF
3)	On PTF, check the received BPDU from Ethernet8 of SONIC DUT. The received BPDU should consists of root bridge as per the PTF generated packet and designated bridge as SONIC DUT, root path cost should be as per the default value set for Ethernet4
4)	Update the port cost of Ethernet4 on SONIC DUT using the config command.
5)	On PTF, verify the received BPDU from Ethernet8 has the root path cost with the configured port cost of Ethernet4.

## TC7: Validate root guard functionality on SONIC DUT
1)	On SONIC DUT enable root guard on Ethernet4 and Ethernet8
2)	From PTF send packets with better bridge priority than SONIC DUT to Ethernet4 and Ethernet8
3)	Verify on SONIC DUT the port is moved into Root inconsistent state
4)	Stop sending the BPDUs from PTF
5)	Verify the ports on SONIC DUT move to forwarding state after 120 seconds

## TC8: Validate BPDU guard functionality on SONIC DUT
1)	On SONIC DUT enable BPDU guard with shutdown enabled on Ethernet4 
2)	From PTF send BPDUs to SONIC DUT on Ethernet4
3)	Verify BPDU guard kicks in and shuts down port Ethernet4, by verifying the operational state of port from APP DB
4)	Disable BPDU guard on the port Ethernet4
5)	Enable port Ethernet4 using CLI command
6)	From PTF send BPDUs to SONIC DUT on Ethernet4
7)	Verify the BPDU guard doesn’t kick in by verifying the Ethernet4 port state is still UP

## TC9: Validate PVST timer configurations
1)	Modify the hello interval from default value to 3 secs
2)	On PTF capture the packet and verify the hello interval in the BPDU is set to 3 secs
3)	Modify the forward delay from default value to 20 secs
4)	On PTF capture the packet and verify the forward delay in the BPDU is set to 20 secs
5)	Modify the max age from default value to 25 secs
6)	On PTF capture the packet and verify the max age in the BPDU is set to 25 secs

## TC10: Validate Backup port functionality
1)	Configure DUT to be the root bridge
2)	On PTF capture the BPDU generated by DUT on Ethernet4 and use same BPDU to send it back on Ethernet8
3)	Verify on DUT port Ethernet8 is moved into blocking state as it receives its own BPDU
4)	Wait for 60seconds and verify port Ethernet8 moves to forwarding state as DUT is not getting its own BPDU now.

## TC11: Validate Mac flush functionality
1)	Verify SONIC DUT is acting as the root bridge by checking the root bridge id in APP DB.
2)	On PTF, capture and validate L2 traffic sent from Ethernet4  to Ethernet8  over VLAN 1000. 
3)	 Ensure that the MAC address is learned on the SONIC DUT for the receiving port Ethernet4.
4)	From PTF, send a TCN BPDU packet to trigger MAC flush.
5)	Verify that MAC address entries on SONIC DUT for Ethernet4 are flushed (reduced in count).



