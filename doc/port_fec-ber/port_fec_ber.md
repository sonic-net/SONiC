# Sonic Port FEC BER #

## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#abbreviations)
- [1 Overview](#1-overview)
- [2 Requirements](#2-requirements)
  - [2.1 Functional requirements](#21-functional-requirements)
  - [2.2 CLI requirements](#22-cli-requirements)
- [3 Architecture Design](#3-architecture-design)
- [4 High level design](#4-high-level-design)
  - [4.1 Assumptions](#41-assumptions)
  - [4.2 SAI counters used](#42-sai-counters-used)
  - [4.3 SAI API](#43-sai-api)
  - [4.4 Calculation formulas](#44-calculation-formulas)
- [5 Sample output](#5-sample-output)



### Revision

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 |             | Vincent (Ping Ching) Ng| Initial version                   |

### Scope

  This document provides information about the implementation of Port Forward Error Correction (FEC) Bit Error Rate (BER) measurement. 
  This new statistic will include correctable bits and uncorrectable bits BER.

### Definitions / Abbreviations

 | Term    |  Definition / Abbreviation                                            |
 |---------|-----------------------------------------------------------------------|
 | FEC     | Forward Error Correction  |
 | BER     | Bits Error Rate, a measure of percentage of transmitted bits that are received incorrectly.  
 | Pre FEC | The number of bits which FEC successfully correct.  
 | Post FEC| The number of bits which FEC fails to correct.  
 | Frame   | Size of each FEC block.  
 | Symbol  | Part of the FEC structure which the error detection and correction base on.  
 | RS-FEC  | Reed Solomon Forward Error correction, RS-544 = 5440 total size , RS-528 = 5280 total size  
 | NRZ     | Non Return to Zero encoding  
 | PAM4    | Pulse Amplitude Modulation 4 level encoding  

### 1 Overview

FEC is a common hardware feature deployed in a high speed interconnect. Due to the signal integrity issue, data being transfer might have bit(s) corruption. The FEC will correct the data's corruption and increment counters to account for corrected bits (Pre FEC) or uncorrected frame (Post FEC)

## 2 Requirements
### 2.1 Functional Requirements
  This HLD is to   
  - enhance the current "show interface counter fec-stat" to include Pre and Post BER statistic as new columns
  - Add Pre and Post FEC BER per interface into Redis DB for telemetry streaming
  - Calculate the Pre and Post FEC BER at the same interval as the PORT_STAT poll rate which is 1 sec.

### 2.2 CLI Requirements

The existing "show interface counter fec-stat" will be enhanced to include two additional columns for BER.  
 - Pre FEC BER  
 - Post FEC BER

## 3 Architecture Design

There are no changes in the current Sonic Architecture.

## 4 High-Level Design

 * SWSS changes:
   + port_rates.lua

      Enhance to collect and compute the BER on each port at the same port state collection interval. It is currently at 1 second.

     - Access the counter_db for counters for SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS & SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES
     - Access to the appl_db to compute the actual serdes speed of the ports and its number of lanes
     - Store the computed BER and the old redis counters value back to the redis DB

 * Utilities Common changes:

   + portstat.py:

     The portstat command with -f , which representing the cli "show interface counter fec-stat" will enhanced to add two new columns, FEC_PRE_BER & FEC_POST_BER

   + netstat.py :

     Add new format support to display the BER in a floating point format


### 4.1 Assumptions

SAI provide access to each interface the following attributes
- SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES
  - return not support if its not working for an interface


### 4.2 Sai Counters Used

The following redis DB entries will be access for the BER calculations

|Redis DB |Table|Entries|New, RW| Format | Descriptions|   
|--------------|-------------|------------------|--------|----------------|----------------|  
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS |R |number |Total number bits corrected</sub>|
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES |R |number |Tota number uncorrectable frame |
|COUNTER_DB |COUNTERS_PORT_NAME_MAP | name & oid  |R |name  |Oid to name mapping |  
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last | New, RW|number |Last corrected bits counts |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last |New, RW|number |Last uncorrctedble frame counts |  
|COUNTER_DB |RATES |FEC_PRE_BER |New, RW| floating |calculated pre fec BER |  
|COUNTER_DB |RATES |FEC_POST_BER |New, RW| floating | calulated post fec BER |  
|APPL_DB |PORT_TABLE |lanes |R |strings |number of serdes lanes in the port |  
|APPL_DB |PORT_TABLE |speed |R |number |port speed |  


### 4.3 SAI API

No change in the SAI API. No new SAI object accessed.


### 4.4 Calculation Formulas

Each port can be made up of multiple lanes and each running at the same serdes speed. The hardware counter is per port basis. Therefore the BER calculation will require to account for #lanes and serdes speed of the port.  The lanes count and port speed can be retrieved from the APPL_DB. Serdes speed will be calculated using port speed / number of lanes.

However in the case of post FEC, the frames are actually dropped. There is no way to tell the actual number of error bits in the frame. The calculation is assuming the worst case where all bits in the frame were corrupted.



```
Pseudocode :

Step 1: get lanes count and port speed
    lanes count  : APPL_DB , hget PORT_TABLE lanes , lane count calculate using string.gsub()
    port speed : APPL_DB , hget PORT_TABLE speed,  speed of the port

Step 2: calculate port_data_rate
    port_data_rate = math.fmod(port speed / number of lanes)

Step 3 : look up link serdes speed
    Look up the serdes speed using the following logic

    if port_data_rate == 1000 then
        serdes = 1.25e+9
    elseif port_data_rate == 10000 then
        serdes = 10.3125e+9
    elseif port_data_rate == 25000 then
        serdes = 25.78125e+9
    elseif port_data_rate == 50000 then
        serdes = 53.125e+9
    elseif port_data_rate == 100000 then
        serdes = 106.25e+9
    else
        serdes = 0
    end

Step 4 : assume statistical average error rate as 1e-8 per frame

     rs_average_frame_ber = 1e-8 

Step 5: calcuate BER

    interval = PORT_STATE poll interval which is 1000 ms currently

    Pre FEC BER = (SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS - SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last) / (serdes * lanes_count * interval / 1000)
    Post FEC BER = (SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last) * rs_average_frame_ber / (serdes * lanes_count * interval / 1000)


Step 6: the following data will be updated and its latest value stored in the COUNTER_DB, RATES table after each iteraction

    Pre FEC BER , Post FEC BEC, SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last and SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last

```
## 5 Sample Output
```
root@ctd615:/usr/local/lib/python3.11/dist-packages/utilities_common#  portstat -f
      IFACE    STATE    FEC_CORR    FEC_UNCORR    FEC_SYMBOL_ERR    FEC_PRE_BER    FEC_POST_BER
-----------  -------  ----------  ------------  ----------------  -------------  --------------
  Ethernet0        U           0             0                 0    1.48e-20       0.00e+00
  Ethernet8        U           0             0                 0    1.98e-19       0.00e+00
 Ethernet16        U           0             0                 0    1.77e-20       0.00e+00
 Ethernet24        U           0             0                 0    4.36e-19       0.00e+00
 Ethernet32        U           0             0                 0    1.93e-19       0.00e+00
 Ethernet40        U           1             0                 1    2.77e-18       0.00e+00
 Ethernet48        U           0             0                 0    8.33e-23       0.00e+00
 Ethernet56        U           0             0                 0    1.48e-55       0.00e+00
 Ethernet64        U           0             0                 0    9.88e-32       0.00e+00
 Ethernet72        U           0             0                 0    4.97e-22       0.00e+00
 Ethernet80        U           0             0                 0    4.10e-19       0.00e+00
 Ethernet88        U           0             0                 0    3.84e-19       0.00e+00
 Ethernet96        U           0             0                 0    4.77e-20       0.00e+00
```

## 6 Unit Test cases

## 7 System Test cases

## 8 Open/Action items - if any


NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
