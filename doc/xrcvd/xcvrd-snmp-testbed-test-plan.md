# SNMP Transceiver Monitoring Testbed Test Plan

## Revision

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             | Stepan Blyschak    | Initial version                   |
 | 0.2 |             |      Liu Kebo      | updated version                   |

## Test Plan

|    Document Name                    | Link     |
|-------------------------------------|----------|
| Transceiver Monitoring Requirements | [Link](https://github.com/stepanblyschak/SONiC/blob/SNMP_Transceiver_Monitoring_Testbed/doc/OIDsforSensorandTransciver.MD)|
| Entity MIB                          | [Link](https://www.ietf.org/rfc/rfc2737.txt)|
| Entity Sensor MIB                   | [Link](https://www.ietf.org/rfc/rfc3433.txt)|
## Overview

Transceiver's and DOM sensor information are now exposed via SNMP according to Transceiver Monitoring Requirements and RFC 2737 & RFC 3433. This document describes the test plan for extending SNMP test to test new MIBs.

## Test structure 

Test cases
----------

### Test case \#1

This test case should check that CHASSIS OID is present in the Entity Table in SNMP facts gathered from DUT.

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     | check whether $CHASSIS_OID in snmp_facts                     | $CHASSIS_OID is present in snmp_facts                   |

### Test case \#2

This test case verify that for each minigraph ports there is an entry in Entity MIB. 

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     | for each item in $minigraph_ports check if there is a MIB entry in Entity MIB                     | All "UP" ports should have MIB entry in Entity MIB                   |
| 2.     | for each item in $minigraph_ports and for each sensor(Tx Power, RX Power, TX bias, Temperature and Voltage of the $item check if there are MIB entries in Entity MIB                     | All "UP" ports should have all sensors MIB entries in Entity MIB                   |

### Test case \#3

This test case verify that for each sensor found in Entity MIB we have an entry in Entity Sensor MIB, regardless of the state of the transceiver sensor or its actual value.

| **\#** | **Test Description** | **Expected Result** |
|--------|----------------------|---------------------|
| 1.     | for each item in $entity_mib_sensors check if there is a MIB entry in Entity Sensor MIB                     | All sensors in Entity MIB should have the an entry in Entity Sensor MIB                   |
