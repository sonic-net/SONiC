# Ragile Fan control HLD #

## Table of Content 

[TOC]

### Revision  

| Rev  | Date | Author | Change Description |
| ---- | ---- | ------ | ------------------ |
|      |      |        |                    |


### Scope  

This document describes the details of fan control design for Ragile device. 

### Definitions/Abbreviations 

| Definitions/Abbreviation | Description                               |
| ------------------------ | ----------------------------------------- |
| MAC                      | Medium access control chip                |
| BOARD                    | Motherboard                               |
| CPU                      | Central processing unit                   |
| INLET                    | Air inlet                                 |
| OUTLET                   | Air onlet                                 |
| CPLD                     | Complex programmable logic device         |
| FPGA                     | Field-programmable gate array             |

| Definitions/Abbreviation | Description                           |
| ------------------------ | ------------------------------------- |
| INLET_T                  | Temperature detection point of INLET  |
| OUTLET_T                 | Temperature detection point of OUTLET |
| CPU_T                    | Temperature detection point of CPU    |
| BOARD_T                  | Temperature detection point of BOARD  |
| MAC_T                    | Temperature detection point of MAC    |

### Overview 

In order to ensure the stable of the networking switch at an appropriate temperature, this document provides an structure of fan control based on the temperature points.

### Requirements

The functional requirements include:

- A stable method of obtaining four temperature points. Like $I^2C$ etc.
- A method to control Fans, like CPLD or FPAG etc.
- An common platform API that encapsulates above content.

### Design 

#### Platform capabilities

- Fan speed is described by 0 ~ 255(0 ~ 0xff) levels, 0 means stopped and 255 means maximum, the default level is 96(0x60)
- The temperature detection points involved are `CPU_T`, `INLET_T`, `OUTLET_T`, `BOARD_T`, `MAC_T`.
- Support fan redundancy.

#### Platform restrictions

- For safety reasons, level 0 is not allowed, the minimum is limit to `51(0x33)`.
- Fans with opposite directions are not allowed.

#### Policy

- When $T_{in}<T_{min}$ keep level 96(0x60).

- When $T_{in}\geq T_{min}$ and device temperature is growing, calculate fan speed following formula:
$$
V_{fan} = V_{min} + k(T_{in} - T_{min})
$$
- When $T_{in} \geq T_{min}$ and device temperature is cooling down, there is two policy:
  - When $T_{last} - T_{curr} \geq T_{fuse}$ use formula above.
  - Otherwise keep the original speed.

| Definitions         | Description                                        |
| ------------------- | -------------------------------------------------- |
| $T_{in}$            | Inlet temperature                                  |
| $T_{min}$           | Minimum allowable temperature                      |
| $T_{max}$           | Maximum allowable temperature                      |
| $V_{fan}$           | Speed of fan                                       |
| $V_{min}$           | Minimum speed of fan                               |
| $V_{max}$           | Maximum speed of fan                               |
| $k$                 | Slope of fan speed and temperature                 |
| $T_{last}$          | Inlet temperature measured last time               |
| $T_{curr}$          | Inlet temperature measured current                 |
| $T_{fuse}$          | Fuse that determine whether to trigger fan control |


#### Emergency policy

- When the device status fails three times in a row, set level as 187(0xbb) until it back to normal. Then restart the control policy.

- There is two way to determine device status:
  1. Error reading temperature point.
  2. $T_{mac} - T_{in} \leq T_{err\_l\_thd}$ or $T_{mac} - T_{in} \geq T_{err\_h\_thd}$
  
- When 

  $T_{mac} \geq T_{mac\_w\_thd}$ or
  $T_{out} \geq T_{out\_w\_thd}$ or
  $T_{board} \geq T_{board\_w\_thd}$ or
  $T_{cpu} \geq T_{cpu\_w\_thd}$ or
  $T_{in} \geq T_{in\_w\_thd}$
  enter the warning alram state, print corresponding log, turn state LED to amber and adjust all Fans to full speed.

- When 

  $T_{mac} \geq T_{mac\_c\_thd}$ or
  $T_{out} \geq T_{out\_c\_thd}$ and $T_{board} \geq T_{board\_c\_thd}$ and $T_{cpu} \geq T_{cpu\_c\_thd}$ and $T_{in} \geq T_{in\_c\_thd}$
  enter critical alarm state, print corresponding log, turn state LED to red. When any one of the following two conditions is met, reset the machine.
  
  - $T_{mac} \geq T_{mac\_c\_thd}$
  - $T_{in} \geq T_{in\_c\_thd}$ and $T_{out} \geq T_{out\_c\_thd}$ and $T_{board} \geq T_{board\_c\_thd}$ and $T_{cpu} \geq T_{cpu\_c\_thd}$
  
- To avoid jitter in the measurement, warning state and crital state need to be verified twice.

| Definitions         | Description                                        |
| ------------------- | -------------------------------------------------- |
| $T_{out}$           | Outlet temperature                                 |
| $T_{mac}$           | MAC temperature                                    |
| $T_{board}$         | BOARD temperature                                  |
| $T_{cpu}$           | CPU temperature                                    |
| $T_{err\_l\_thd}$   | Error temperature low threshold, default is -50C°  |
| $T_{err\_h\_thd}$   | Error temperature high threshold default is 50C°   |
| $T_{mac\_w\_thd}$   | MAC warning temperature threshold                  |
| $T_{mac\_c\_thd}$   | MAC critical temperature threshold                 |
| $T_{out\_w\_thd}$   | OUTLET warning temperature threshold               |
| $T_{out\_c\_thd}$   | OUTLET critical temperature threshold              |
| $T_{in\_w\_thd}$    | INLET warning temperature threshold                |
| $T_{in\_c\_thd}$    | INLET critical temperature threshold               |
| $T_{cpu\_w\_thd}$   | CPU warning temperature threshold                  |
| $T_{cpu\_c\_thd}$   | CPU critical temperature threshold                 |
| $T_{board\_w\_thd}$ | BOARD warning temperature threshold                |
| $T_{board\_c\_thd}$ | BOARD critical temperature threshold               |

### SAI API 

NA

### Configuration and management 

NA

#### CLI/YANG model Enhancements 

NA

#### Config DB Enhancements  

NA
		
### Warmboot and Fastboot Design Impact  

NA

### Restrictions/Limitations  

NA

### Testing Requirements/Design  

NA

#### Unit Test cases

Run command `show platform fan status` to check current fan speed, alias **FAN_SPEED**

- Pluging out one or more fans, check FAN_SPEED is it running at full speed after 
- Heating up chips to warning threshold, check FAN_SPEED is it running at full speed.
- Heating up chips to critical threshold, check system is it reset.

#### System Test cases

NA

### Open/Action items - if any 

NA