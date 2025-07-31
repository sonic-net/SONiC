# Feature Name #

Fan control policy for ragile device.

## High Level Design Document

Rev 0.1

## Table of Content 

* [Feature Name](#feature-name)
   * [High Level Design Document](#high-level-design-document)
   * [Table of Content](#table-of-content)
      * [Revision](#revision)
      * [Scope](#scope)
      * [Definitions/Abbreviations](#definitionsabbreviations)
      * [Overview](#overview)
      * [Requirements](#requirements)
      * [Design](#design)
         * [Platform capabilities](#platform-capabilities)
         * [Platform restrictions](#platform-restrictions)
         * [Policy](#policy)
         * [Emergency policy](#emergency-policy)
      * [SAI API](#sai-api)
      * [Configuration and management](#configuration-and-management)
         * [CLI/YANG model Enhancements](#cliyang-model-enhancements)
         * [Config DB Enhancements](#config-db-enhancements)
      * [Warmboot and Fastboot Design Impact](#warmboot-and-fastboot-design-impact)
      * [Restrictions/Limitations](#restrictionslimitations)
      * [Testing Requirements/Design](#testing-requirementsdesign)
         * [Unit Test cases](#unit-test-cases)
         * [System Test cases](#system-test-cases)
      * [Open/Action items - if any](#openaction-items---if-any)

### Revision  

| Rev  | Date       | Author      | Change Description |
| ---- | ---------- | ----------- | ------------------ |
| 0.1  | 09/22/2021 | Ragile Team | Initial version    |


### Scope  

This document gives the details of fan control design for Ragile device. 

### Definitions/Abbreviations 

| Definitions/Abbreviation | Description                               |
| ------------------------ | ----------------------------------------- |
| MAC                      | Medium access control chip                |
| BOARD                    | Motherboard                               |
| CPU                      | Central processing unit                   |
| INLET                    | Air inlet                                 |
| OUTLET                   | Air onlet                                 |
| CPLD                     | Complex programmable logic device |
| FPGA                     | Field-programmable gate array     |

| Definitions/Abbreviation | Description                           |
| ------------------------ | ------------------------------------- |
| INLET_T                  | Temperature detection point of INLET  |
| OUTLET_T                 | Temperature detection point of OUTLET |
| CPU_T                    | Temperature detection  point of CPU   |
| BOARD_T                  | Temperature detection point of BOARD  |
| MAC_T                    | Temperature detection point of MAC    |

### Overview 

In order to ensure the stable of the networking switch at an appropriate temperature, this document provides an structure of fan control based on the temperature points.

### Requirements

The functional requirements include:

- A stable method of obtaining four temperature points. Like <!-- $I^2C$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=I%5E2C"> etc.
- A method to control Fans, like CPLD or FPAG etc.
- An common platform API that encapsulates above content.

### Design 

#### Platform capabilities

- Fan speed is described by 0 ~ 255(0 ~ 0xff) levels, 0 means stopped and 255 means maximum, the default level is `96(0x60)`
- The temperature detection points involved are `CPU_T`, `INLET_T`, `OUTLET_T`, `BOARD_T`, `MAC_T`.
- Support fan redundancy.

#### Platform restrictions

- For safety reasons, level `0` is not allowed, the minimum is limit to `51(0x33)`.
- Fans with opposite directions are not allowed.

#### Policy

- When <!-- $T_{in}<T_{min}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D%3CT_%7Bmin%7D"> keep level `96(0x60)`.

- When <!-- $T_{in}\geq T_{min}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D%5Cgeq%20T_%7Bmin%7D"> and device temperature is growing, calculate fan speed following formula:
<!-- $$
V_{fan} = V_{min} + k(T_{in} - T_{min})
$$ --> 

<div align="center"><img style="background: white;" src="https://render.githubusercontent.com/render/math?math=V_%7Bfan%7D%20%3D%20V_%7Bmin%7D%20%2B%20k(T_%7Bin%7D%20-%20T_%7Bmin%7D)"></div>

- When <!-- $T_{in} \geq T_{min}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D%20%5Cgeq%20T_%7Bmin%7D"> and device temperature is cooling down, there is two policy:
  - When <!-- $T_{last} - T_{curr} \geq T_{fuse}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Blast%7D%20-%20T_%7Bcurr%7D%20%5Cgeq%20T_%7Bfuse%7D"> use formula above.
  - Otherwise keep the original speed.

| Definitions         | Description                                        |
| ------------------- | -------------------------------------------------- |
| <!-- $T_{in}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D">            | Inlet temperature                                  |
| <!-- $T_{min}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmin%7D">           | Minimum allowable temperature                      |
| <!-- $T_{max}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmax%7D">           | Maximum allowable temperature                      |
| <!-- $V_{fan}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=V_%7Bfan%7D">           | Speed of fan                                       |
| <!-- $V_{min}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=V_%7Bmin%7D">           | Minimum speed of fan                               |
| <!-- $V_{max}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=V_%7Bmax%7D">           | Maximum speed of fan                               |
| <!-- $k$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=k">                 | Slope of fan speed and temperature                 |
| <!-- $T_{last}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Blast%7D">          | Inlet temperature measured last time               |
| <!-- $T_{curr}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcurr%7D">          | Inlet temperature measured current                 |
| <!-- $T_{fuse}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bfuse%7D">          | Fuse that determine whether to trigger fan control |


#### Emergency policy

- When the device status fails three times in a row, set level as `187(0xbb)` until it back to normal. Then restart the control policy.

- There is two way to determine device status:
  1. Error reading temperature point.
  2. <!-- $T_{mac} - T_{in} \leq T_{err\_l\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D%20-%20T_%7Bin%7D%20%5Cleq%20T_%7Berr%5C_l%5C_thd%7D"> or <!-- $T_{mac} - T_{in} \geq T_{err\_h\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D%20-%20T_%7Bin%7D%20%5Cgeq%20T_%7Berr%5C_h%5C_thd%7D">
  
- When 

  <!-- $T_{mac} \geq T_{mac\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D%20%5Cgeq%20T_%7Bmac%5C_w%5C_thd%7D"> or
  <!-- $T_{out} \geq T_{out\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%7D%20%5Cgeq%20T_%7Bout%5C_w%5C_thd%7D"> or
  <!-- $T_{board} \geq T_{board\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bboard%7D%20%5Cgeq%20T_%7Bboard%5C_w%5C_thd%7D"> or
  <!-- $T_{cpu} \geq T_{cpu\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%7D%20%5Cgeq%20T_%7Bcpu%5C_w%5C_thd%7D"> or
  <!-- $T_{in} \geq T_{in\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D%20%5Cgeq%20T_%7Bin%5C_w%5C_thd%7D">
  enter the warning alram state, print corresponding log, turn state LED to amber and adjust all Fans to full speed.

- When 

  <!-- $T_{mac} \geq T_{mac\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D%20%5Cgeq%20T_%7Bmac%5C_c%5C_thd%7D"> or
  <!-- $T_{out} \geq T_{out\_c\_thd}$ and $T_{board} \geq T_{board\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%7D%20%5Cgeq%20T_%7Bout%5C_c%5C_thd%7D%24%20and%20%24T_%7Bboard%7D%20%5Cgeq%20T_%7Bboard%5C_c%5C_thd%7D"> and <!-- $T_{cpu} \geq T_{cpu\_c\_thd}$ and $T_{in} \geq T_{in\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%7D%20%5Cgeq%20T_%7Bcpu%5C_c%5C_thd%7D%24%20and%20%24T_%7Bin%7D%20%5Cgeq%20T_%7Bin%5C_c%5C_thd%7D">
  enter critical alarm state, print corresponding log, turn SYS_LED to red. When any one of the following two conditions is met, reset the machine.
  
  - <!-- $T_{mac} \geq T_{mac\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D%20%5Cgeq%20T_%7Bmac%5C_c%5C_thd%7D">
  - <!-- $T_{in} \geq T_{in\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%7D%20%5Cgeq%20T_%7Bin%5C_c%5C_thd%7D"> and <!-- $T_{out} \geq T_{out\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%7D%20%5Cgeq%20T_%7Bout%5C_c%5C_thd%7D"> and <!-- $T_{board} \geq T_{board\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bboard%7D%20%5Cgeq%20T_%7Bboard%5C_c%5C_thd%7D"> and <!-- $T_{cpu} \geq T_{cpu\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%7D%20%5Cgeq%20T_%7Bcpu%5C_c%5C_thd%7D">
  
- To avoid jitter in the measurement, warning state and crital state need to be verified twice.

| Definitions         | Description                                        |
| ------------------- | -------------------------------------------------- |
| <!-- $T_{out}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%7D">           | Outlet temperature                                 |
| <!-- $T_{mac}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%7D">           | MAC temperature                                    |
| <!-- $T_{board}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bboard%7D">         | BOARD temperature                                  |
| <!-- $T_{cpu}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%7D">           | CPU temperature                                    |
| <!-- $T_{err\_l\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Berr%5C_l%5C_thd%7D">   | Error temperature low threshold, default is -50C°  |
| <!-- $T_{err\_h\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Berr%5C_h%5C_thd%7D">   | Error temperature high threshold default is 50C°   |
| <!-- $T_{mac\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%5C_w%5C_thd%7D">   | MAC warning temperature threshold                  |
| <!-- $T_{mac\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bmac%5C_c%5C_thd%7D">   | MAC critical temperature threshold                 |
| <!-- $T_{out\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%5C_w%5C_thd%7D">   | OUTLET warning temperature threshold               |
| <!-- $T_{out\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bout%5C_c%5C_thd%7D">   | OUTLET critical temperature threshold              |
| <!-- $T_{in\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%5C_w%5C_thd%7D">    | INLET warning temperature threshold                |
| <!-- $T_{in\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bin%5C_c%5C_thd%7D">    | INLET critical temperature threshold               |
| <!-- $T_{cpu\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%5C_w%5C_thd%7D">   | CPU warning temperature threshold                  |
| <!-- $T_{cpu\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bcpu%5C_c%5C_thd%7D">   | CPU critical temperature threshold                 |
| <!-- $T_{board\_w\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bboard%5C_w%5C_thd%7D"> | BOARD warning temperature threshold                |
| <!-- $T_{board\_c\_thd}$ --> <img style="transform: translateY(0.1em); background: white;" src="https://render.githubusercontent.com/render/math?math=T_%7Bboard%5C_c%5C_thd%7D"> | BOARD critical temperature threshold               |

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
