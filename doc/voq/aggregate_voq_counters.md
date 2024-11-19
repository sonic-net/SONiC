# Aggregate VOQ Counters in SONiC #
#### Rev 1.0

## Table of Content
   * [Revision](#revision)
   * [Overview](#overview)
   * [Requirements](#requirements)
   * [Architecture Design](#architecture-design)
   * [High-Level Design](#high-level-design)
      * [Database changes](#database-changes)
      * [Repositories that need to be changed](#repositories-that-need-to-be-changed)
   * [SAI API](#sai-api)
   * [Configuration and management](#configuration-and-management)
      * [CLI](#cli)
   * [Testing Requirements/Design](#testing-requirementsdesign)
      * [System Test cases](#system-test-cases)  

### Revision 
| Rev |     Date    |       Author                                                                       | Change Description                |
|:---:|:-----------:|:----------------------------------------------------------------------------------:|-----------------------------------|
| 1.0 | 19-Nov-2024 | Harsis Yadav, Pandurangan R S, Vivek Kumar Verma (Arista Networks)               | Initial public version            | 

### Overview 

In a [distributed VOQ architecture](https://github.com/sonic-net/SONiC/blob/master/doc/voq/architecture.md) corresponding to each output VOQ present on an ASIC, there are VOQs present on every ASIC in the system. Each ASIC has its own set of VOQ stats maintained in the FSI that have to be gathered independently and can be hard to visualize, providing a non-cohesive experience.

### Requirements

Provide aggregate VOQ counters in a distributed VOQ architecture.

### Architecture Design 

No new architecture changes are required to SONiC. 

### High-Level Design





