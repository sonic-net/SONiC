# FEC FLR support in SONiC #

## Table of Content
- [Revision](#revision)
- [Scope](#scope)
- [Definitions/Abbreviations](#abbreviations)
- [1 Overview](#1-overview)
- [2 Requirements](#2-requirements)
  - [2.1 Functional Requirements](#21-functional-requirements)
  - [2.2 CLI Requirements](#22-cli-requirements)
- [3 Architecture Design](#3-architecture-design)
- [4 High level design](#4-high-level-design)
  - [4.1 Assumptions](#41-assumptions)
  - [4.2 SAI counters used](#42-sai-counters-used)
  - [4.3 SAI API](#43-sai-api)
  - [4.4 FEC interleaving](#44-fec-interleaving)
  - [4.5 Calculation formulas](#45-calculation-formulas)
- [5 Sample output](#5-sample-output)

### Revision

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 | 19-Mar-2025 | Pandurangan R S, Vinod Kumar Reddy Jammala (Arista Networks)| Initial version                   |

### Scope

This document provides information about the implementation of Port Forward Error Correction (FEC) Frame Loss Ratio (FLR) support in SONiC.

### Definitions/Abbreviations

 | Term    |  Definition / Abbreviation                                            |
 |---------|-----------------------------------------------------------------------|
 | CER     | Codeword Error Ratio  |
 | FEC     | Forward Error Correction  |
 | FLR     | Frame Loss Ratio  |

### 1 Overview
Frame Loss Ratio (FLR) is a key performance metric used to measure the percentage of lost frames relative to the total transmitted frames over a network link.

FLR is expressed as,
	FLR = (Total Transmitted Frames - Total Received Frames) / Total Transmitted Frames

Based on the Forward Error Correction (FEC) data, receiver device can compute Codeword Error Ratio (CER) which is expressed as

	CER = Uncorrectable FEC codewords / Total FEC codewords Received

and FEC FLR can be estimated from CER.

## 2 Requirements
### 2.1 Functional Requirements
  This HLD is to
  - Calculate the FEC FLR at the same interval as the PORT_STAT poll rate which is 1 sec.
  - Add FEC FLR per interface into Redis DB for telemetry streaming.
  - Enhance the current "show interfaces counters fec-stats" to include FEC FLR statistics as a new column.

### 2.2 CLI Requirements

The existing "show interfaces counters fec-stats" will be enhanced to include FEC_FLR column.
 - FEC_FLR

## 3 Architecture Design

There are no changes to the current SONiC Architecture.

## 4 High-Level Design

 * SWSS changes:
   + port_rates.lua

      Enhance to collect and compute the FEC FLR on each port at the same port stat collection interval (Current default value is 1 second).

     - Access the COUNTER_DB for already available counters for SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES, SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES, and SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0.
     - Store the computed FEC FLR and previous redis counter values back to the redis DB.

 * Utilities Common changes:

   + portstat.py:

     The portstat command with -f, representing the cli "show interfaces counters fec-stats" will be enhanced to add FEC_FLR column.


### 4.1 Assumptions

SAI provide access to each interface the following attributes
- SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES, which represents the number of uncorrectable FEC codewords.
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES, which represents the number of correctable FEC codewords.
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0, which represents the number of codewords without any errors.
  - return not support if its not working for an interface


### 4.2 Sai Counters Used

The following redis DB entries will be accessed for the FEC FLR calculations

|Redis DB |Table|Entries|New, RW| Format | Description|
|--------------|-------------|------------------|--------|----------------|----------------|
|COUNTER_DB |COUNTERS_PORT_NAME_MAP | oid  |R |string |Name to oid mapping |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES |R |number |Total number of uncorrectable codewords |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES |R |number |Total number of correctable codewords |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0 |R |number |Total number of codewords without any errors |
|COUNTER_DB |RATES |FEC_FLR |New, RW| floating |calculated FEC FLR |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last |NEW, RW |number |Last uncorrectable codewords |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last |NEW, RW |number |Last correctable codewords |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0_last |NEW, RW |number |Last codewords without any errors |


### 4.3 SAI API

No change in the SAI API. No new SAI object accessed.

### 4.4 FEC interleaving
With FEC interleaving factor (X) incorporated, As per [IEEE 802.3df Logic Ad Hoc](https://www.ieee802.org/3/df/public/adhoc/logic/22_0630/opsasnick_3df_logic_220630a.pdf) FEC FLR is expressed as

For X=1 (no interleaving), FEC_FLR = 1.125 * CER <br>
For X=2, FEC_FLR = 2.125 * CER <br>
For X=4, FEC_FLR = 4.125 * CER

By default we consider "no interleaving" and thus FEC_FLR will be computed as "1.125 * CER".

To include the interleaving factor in FEC_FLR computation, a new SAI port attribute will be needed to retrieve the underlying interleaving factor.

### 4.5 Calculation Formulas

```
Step 1: calculate CER per PORT_STAT poll interval (default 1s)

    CER = Uncorrectable FEC codewords / (Uncorrectable FEC codewords + Correctable FEC codewords)

    where, Uncorrectable FEC codewords = SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last
	   Correctable FEC codewords = SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last +
				       SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0 - SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0_last

Step 2: calculate FEC FLR using CER and considering interleaving factor (X)
    If X=1, FEC_FLR = 1.125 * CER

Step 3: the following data will be updated and its latest value will be stored in the COUNTER_DB:RATES table after each computation

    FEC_FLR, SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last, SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last and SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0_last

```

## 5 Sample Output
```
admin@qsd220:~$ portstat -f
      IFACE    STATE    FEC_CORR    FEC_UNCORR    FEC_SYMBOL_ERR    FEC_PRE_BER    FEC_POST_BER    FEC_FLR
-----------  -------  ----------  ------------  ----------------  -------------  --------------  ---------
  Ethernet0        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
  Ethernet8        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet16        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet24        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet32        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet40        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet48        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet56        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet64        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet72        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet80        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet88        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
 Ethernet96        U           0             0                 0    0.00e+00       0.00e+00        0.00e+00
```

In case FEC is not supported, FEC_FLR field will display "N/A" in the corresponding entry.

## 6 Unit Test cases

## 7 System Test cases

## 8 Open/Action items - if any

