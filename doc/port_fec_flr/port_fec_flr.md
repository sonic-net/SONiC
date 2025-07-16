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
  - [4.5 Observed FEC FLR](#45-observed-fec-flr)
  - [4.6 Predicted FEC FLR](#46-predicted-fec-flr)
- [5 Sample output](#5-sample-output)

### Revision

  | Rev |     Date    |       Author           | Change Description                |
  |:---:|:-----------:|:----------------------:|-----------------------------------|
  | 0.1 | 19-Mar-2025 | Pandurangan R S, Vinod Kumar Jammala (Arista Networks)| Initial version                   |
  | 0.2 | 07-Jul-2025 | Apoorv Sachan, Pandurangan R S, Vinod Kumar Jammala (Arista Networks)| Add predicted FEC FLR		|

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

Based on the Forward Error Correction (FEC) data, receiver device can compute and estimate Codeword Error Ratio (CER), and FEC FLR will be calculated from CER.

## 2 Requirements
### 2.1 Functional Requirements
  This HLD is to
  - Calculate the FEC FLR at an interval 120 secs.
  - Add FEC FLR per interface into Redis DB for telemetry streaming.
  - Enhance the current "show interfaces counters fec-stats" to include FEC FLR statistics as a new column.

### 2.2 CLI Requirements

The existing "show interfaces counters fec-stats" will be enhanced to include FEC FLR columns.
 - FEC_FLR
 - FEC_FLR_PREDICTED

## 3 Architecture Design

There are no changes to the current SONiC Architecture.

## 4 High-Level Design

 * SWSS changes:
   + port_rates.lua

      Enhance to collect and compute the FEC FLR on each port at an interval of 120 secs.

     - Access the COUNTER_DB for already available counters for SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES, SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES,
       and SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si representing codewords with i symbol errors where i ranges from 0 to 15 in case of RS-544 FEC.
     - Store the computed FEC FLR (observed and predicted) and previous redis counter values back to the redis DB.

 * Utilities Common changes:

   + portstat.py:

     The portstat command with -f, representing the cli "show interfaces counters fec-stats" will be enhanced to add FEC_FLR and FEC_FLR_PREDICTED columns.


### 4.1 Assumptions

SAI provide access to each interface the following attributes
- SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES, which represents the number of uncorrectable FEC codewords.
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES, which represents the number of correctable FEC codewords.
  - return not support if its not working for an interface
- SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si, which represents the number of codewords with i symbol errors.
  - return not support if its not working for an interface


### 4.2 Sai Counters Used

The following redis DB entries will be accessed for the FEC FLR calculations

|Redis DB |Table|Entries|New, RW| Format | Description|
|--------------|-------------|------------------|--------|----------------|----------------|
|COUNTER_DB |COUNTERS_PORT_NAME_MAP | oid  |R |string |Name to oid mapping |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES |R |number |Total number of uncorrectable codewords |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES |R |number |Total number of correctable codewords |
|COUNTER_DB |COUNTERS |SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si |R |number |Total number of codewords with i symbol errors |
|COUNTER_DB |RATES |FEC_FLR |New, RW| floating |calculated observed FEC FLR |
|COUNTER_DB |RATES |FEC_FLR_PREDICTED |New, RW| floating |calculated predicted FEC FLR |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last |NEW, RW |number |Last uncorrectable codewords |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last |NEW, RW |number |Last correctable codewords |
|COUNTER_DB |RATES |SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si_last |NEW, RW |number |Last codewords with i symbol errors |


### 4.3 SAI API

No change in the SAI API. No new SAI object accessed.

### 4.4 FEC interleaving
With FEC interleaving factor (X) incorporated, As per [IEEE 802.3df Logic Ad Hoc](https://www.ieee802.org/3/df/public/adhoc/logic/22_0630/opsasnick_3df_logic_220630a.pdf) FEC FLR is expressed as

For X=1 (no interleaving), FEC_FLR = 1.125 * CER <br>
For X=2, FEC_FLR = 2.125 * CER <br>
For X=4, FEC_FLR = 4.125 * CER

By default we consider "no interleaving" and thus FEC FLR will be computed as "1.125 * CER".

To include the interleaving factor in FEC FLR computation, a new SAI port attribute will be needed to retrieve the underlying interleaving factor.

### 4.5 Observed FEC FLR

```
Step 1: calculate observed CER per poll interval
    Observed CER is expressed as, CER = Uncorrectable FEC codewords / Total FEC codewords Received, which can be expanded to

    CER = Uncorrectable FEC codewords / (Uncorrectable FEC codewords + Codewords with no symbol errors + Correctable FEC codewords)

    where, Uncorrectable FEC codewords = SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last
           Codewords with no symbol errors = SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0 - SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0_last
	   Correctable FEC codewords = SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES - SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last


Step 2: calculate FEC FLR using CER and considering interleaving factor (X)
    If X=1, FEC_FLR = 1.125 * CER


Step 3: the following data will be updated and its latest value will be stored in the COUNTER_DB:RATES table after each computation

    FEC_FLR, SAI_PORT_STAT_IF_IN_FEC_NOT_CORRECTABLE_FRAMES_last, SAI_PORT_STAT_IF_IN_FEC_CORRECTABLE_FRAMES_last and SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_S0_last

```

### 4.6 Predicted FEC FLR

The goal is to estimate FEC FLR by extrapolating from observed codeword error distribution.
```
Step 1: Prepare codeword error index vector (x)

    x = { 1, 2, ..., max_correctable_cw_symbol_errors }

    where, max_correctable_cw_symbol_errors = 15 in case of RS-544

    For each index i in vector x, codeword_errors[i] represents number of codewords with i symbol errors i.e SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si.


Step 2: Compute logarithm codeword error ratio vector (y)

    Codeword error ratio typically follows a exponential decay curve. By applying a logarithm to the codeword error ratio, this curve is transformed into a linear pattern,
    making it suitable for linear regression modeling.

    For each index i in vector x, compute logarithm of codeword error ratio y[i] as follows

    y[i] = log10( codeword_errors[i] / total_codewords )
    where, total_codewords is total number of codewords i.e Σ from i=0 to 15 of SAI_PORT_STAT_IF_IN_FEC_CODEWORD_ERRORS_Si


Step 3: Perform linear regresion to arrive at slope and intercept

    slope = (n * Σ(x*y) - Σx * Σy) / (n * Σ(x²) - (Σx)²)
    intercept = (Σy - slope * Σx) / n
    where, n: number of data points (length of x or y vector)

    This gives the best-fit line, y = slope * x + intercept.


Step 4: Compute extrapolated CER

    Using linear regression line, predicted CER for an index representing j symbol errors is
    predicted_cer_j = 10 ^ ( j * slope + intercept )

    Predicted cer for a window of codewords having uncorrectable symbol errors is
    predicted_cer = Σ from j=16 to 20 of predicted_cer_j
 

Step 5: Compute FLR from extrapolated CER by considering interleaving factor
   If X=1, FEC_FLR_PREDICTED = 1.125 * predicted_cer
   If X=2, FEC_FLR_PREDICTED = 2.125 * predicted_cer


Step 6: Store FEC_FLR_PREDICTED in the COUNTER_DB:RATES table
```

## 5 Sample Output
```
admin@qsd220:~$ portstat -f
      IFACE    STATE    FEC_CORR    FEC_UNCORR    FEC_SYMBOL_ERR    FEC_PRE_BER    FEC_POST_BER    FEC_FLR    FEC_FLR_PREDICTED
-----------  -------  ----------  ------------  ----------------  -------------  --------------  ---------  -------------------
  Ethernet0        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
  Ethernet8        U           0             0                 0    0.00e+00       0.00e+00	  0.00e+00             0.00e+00
 Ethernet16        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet24        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet32        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet40        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet48        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet56        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet64        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet72        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet80        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet88        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
 Ethernet96        U           0             0                 0    0.00e+00       0.00e+00       0.00e+00             0.00e+00
```

In case FEC is not supported, FEC_FLR and FEC_FLR_PREDICTED fields will display "N/A" in the corresponding entry.

## 6 Unit Test cases

## 7 System Test cases

## 8 Open/Action items - if any

