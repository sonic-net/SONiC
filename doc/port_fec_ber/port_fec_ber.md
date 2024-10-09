# Sonic Port FEC BER #

## Table of Content 
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviation](#abbreviations)
- [1 Overview](#1-overview)
  - [1.1 Functional requirements](#11-functional-requirements)
  - [1.2 CLI requirements](#12-cli-requirements)
- [2 Architecture Design](#2-architecture-design)
- [3 High level design](#3-high-level-design)
  - [3.1 Assumptions](#31-assumptions)
  - [3.2 SAI counters used](#32-sai-counters-used)
  - [3.3 SAI API](#33-sai-api)
  - [3.4 Calculation formulas](#34-calculation-formulas)
 

### Revision  

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 |             | Vincent (Ping Ching) Ng| Initial version                   |

### Scope  

  This document provide information about the implementation of Port Forward Error Correction (FEC) Bit Error Rate (BER) measurement. 
  This new statistic will include correctable bits and uncorrectable bits BER.

### Abbreviations 

  FEC        - Forward Error Correction.  
  BER        - Bits Error Rate, measure in bit per second.  
  Pre FEC    - The number of bits which FEC successsfully correct.  
  Post FEC   - The number of bits which FEC fail to correct.  
  Frame      - size of each FEC block.  
  Symbol     - part of the FEC structure which the error detection and correction base on.  
  RS-FEC     - Reed Solomon Forward Error correction, RSFEC-544 = 5440 total size , RSFEC-528 = 5280 total size  
  NRZ        - Non Return to Zero encoding  
  PAM4       - Pulse Amplitude Modulation 4 level eocoding  

### 1 Overview 

#### FEC is a common hardware feature deployed in a high speed interconnect. Due to the signal integrity issue, date being tarnsfer might have bit(s) corrupted. The FEC will correct the data's corruptiom and increment counters to account for corrected bits (Pre FEC) or uncorrected frame (Post FEC)

#### 1.1 Functional Requirements
#####  This HLD is to   
#####  - enhance the current "show interface counter fec-stat" to include Pre and Post BER statistic as new columns
#####  - Add Pre and Post FEC BER per interface into Redis DB for telemetry streaming
#####  - Calculate the Pre and Post FEC BER at the same intervale as the PORT_STAT poll rate which is 1 sec.

#### 1.2 CLI Requirements

##### The existing "show interface counter fec-stat" will enhanced to include two additional columns for BER (b/s).   
##### - Pre FEC BER  
##### - Post FEC BER
     
### 2 Architecture Design

#### There is no changes in the current Sonic Architecture. 


### 3 High-Level Design 

 * SWSS changes:  
   + port_rates.lua
     
     ##### Enhance to collect and compute the BER on each ports at one sec interval. This is the same as the existing port stats collection rate.
     
     ##### - Access the counter_db for counters for SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS & SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES
     ##### - Access to the appl_db to compute the actual serdes speed of the ports and its number of lanes
     ##### - Store the computed BER and the old redis counters value back to the redis DB

 * Utilities Common changes:
 
   + portstat.py:
     
     ##### The portstat command with -f , which representing the cli "show interface counter fec-stat" will enhanced to add two new columns, FEC_PRE_BER & FEC_POST_BER
  
   + netstat.py :
     
     ##### Add new format support to diplay the BER in a floating point format in b/s


### 3.1 Assumptions

#### SAI provide access to each interface the following attributes
- SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS
  - monotonically increasing
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES
  - monotonically increasing
  - return not support if its not working for an interface


### 3.2 Sai Counters Used

#### The following redis DB entries will be access for the BER calculations 

|Redis DB |Table|Entries|New, RW| Format | Descriptions|   
|--------------|-------------|------------------|--------|----------------|----------------|  
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS |R |number |Total number bits corrected</sub>|
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES |R |number |Tota number uncorrectable frame |
|COUNTER_DB |COUNTERS_PORT_NAME_MAP |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES|R |number |Oid to name mapping |  
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last | New, RW|number |Last corrected bits counts |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last |New, RW|number |Last uncorrctedble frame counts |  
|COUNTER_DB |RATES |FEC_PRE_BER |New, RW| floating |calculated pre fec BER |  
|COUNTER_DB |RATES |FEC_POST_BER |New, RW| floating | calulated post fec BER |  
|APPL_DB |PORT_TABLE |lanes |R |strings |number of serdes lanes in the port |  
|APPL_DB |PORT_TABLE |speed |R |number |port speed |  


### 3.3 SAI API 

#### No change in the SAI API. No new SAI object accessed.   


### 3.4 Calculation Formulas

#### Each port can made up of multiple lanes and each running at same serdes speed. The hardware counters is per port basis. Therefore the BER calculation will require to accounts for #lanes and serdes speed of the port.  The lanes count and port speed can be retrive from the APPL_DB. The serdes speed will be calcuate using port speed / number of lanes.
#### However in the case of post FEC, the farme were actually dropped. There is no way to tell the actually number of error bits in the frames. The calculation is assuming the worst case which is the all bits in the frame were corrupted.

- 

```
Pseudocode :

Step 1: get lanes count and port speed
    lanes count  : APPL_DB , hget PORT_TABLE lanes , lane count calculate using string.gsub()
    port speed : APPL_DB , hget PORT_TABLE speed,  speed of the port

Step 2: calculate user_port_lane_speed
    user_port_lane_speed = math.fmod(port speed / number of lanes)

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

Step 4 : frame size

     /* NRZ encoding RDFEC-52 8*/
    if the user speed < 25G
      frame_size = 528
    else /* PAM4 encoding RSFEC-544 */

Step 5: calcuate BER

Pre FEC BER = (SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS - SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last) / delta in sec
Post FEC BER = (SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last) * "frame size" * 10 / delta in sec

Step 6: the following data will be updated and its latest value stored in the COUNTER_DB, RATES table after each iteraction
    Pre FEC BER , Post FEC BEC, SAI_PORT_STAT_IF_IN_FEC_CORRECTED_BITS_last and SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last

```


#### Unit Test cases  

#### System Test cases

### Open/Action items - if any 

	
NOTE: All the sections and sub-sections given above are mandatory in the design document. Users can add additional sections/sub-sections if required.
