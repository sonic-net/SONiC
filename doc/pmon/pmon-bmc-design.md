# SONiC BMC Platform Management & Monitoring #

# Table of Contents

  * [Revision](#revision)
  * [Scope](#scope)
  * [Acronyms](#acronyms)
  * [1. SONiC Platform Management and Monitoring](#1-sonic-platform-management-and-monitoring)
    * [1.1 Functional Requirements](#11-functional-requirements)
    * [1.2 BMC Platform Stack](#12-bmc-platform-stack)
  * [2. Detailed Workflow](#2-detailed-workflow)
    * [2.1 BMC Boot Process](#21-bmc-boot-process)
      * [2.1.1 BMC Rack Manager Interaction](#211-bmc-rack-manager-interaction)
      * [2.1.2 Midplane Ethernet](#212-midplane-ethernet)
      * [2.1.3 BMC Host CPU Interaction](#213-bmc-host-cpu-interaction)
      * [2.1.4 BMC leak_detection_and_thermal policy](#214-bmc-leak-detection-and-thermal-policy)
    * [2.2 BMC Platform Management](#22-bmc-platform-management)
      * [2.2.1 BMC Monitoring and bmcctld](#221-bmc-monitoring-and-bmcctld)
      * [2.2.2 Thermalctld](#222-thermalctld)
      * [2.2.3 Hw watchdog](#223-hw-watchdog)
      * [2.2.4 Platform APIs](#224-platform-apis)
  * [3 Future Items](#3-future-items)
      
### Revision ###

 | Rev |     Date    |       Author                                                            | Change Description                |
 |:---:|:-----------:|:-----------------------------------------------------------------------:|-----------------------------------|
 | 1.0 |             |       SONiC BMC team                                                    | Initial version                   |

# Scope
This document provides design requirements and interactions between platform drivers and PMON for SONiC on BMC 

# Acronyms
BMC - Baseboard Management Controller

Redfish - standard REST API for managing hardware

PMON - Platform Monitor. Used in the context of Platform monitoring docker/processes.

## 1. SONiC Platform Management and Monitoring


### 1.1. Functional Requirements
This section captures the functional requirements for platform monitoring and management in sonic BMC 

* BMC will manage the Host CPU to support operations like power up/down, get operational status.
* BMC will read board leak sensors and take appropriate actions based on policy. 
* BMC will get inputs on liquid temperature, pressure and rack-leak external Rack Manager via redfish protocol.It takes action based on policy
* BMC can be accessed via the external management interface or from the Host CPU via the internal midplane ethernet.

### 1.2. BMC Platform Stack

## 2. Detailed Workflow

### 2.1 BMC Boot Process
- BMC Power on triggered on power supply ON, or external rack-manager power-on command, wait for 3 sec - check for any leaks, thermal violations else power up Host_switch_cpu

#### 2.1.1 BMC Rack Manager Interaction
- bmcweb translates redfish call, use the dbus bridge to hadle GET/POST calls
- GET request will get from redis db
- POST request eg: power on/off will write in redis and bcmctrl daemon reads it.

#### 2.1.2 Midplane Ethernet
- usb ethernet interface with conmmon ip configured in sonic space for host_cpu end, bmc_end

#### 2.1.3 BMC - Host CPU Interaction
- BMC to power on and off the Host CPU/ASIC and other components as needed using platform API
- Get the thermal data from Host thermal sensors

- Power ON Host

- Power off Host
-  Can we do this gracefully, like if switch is inProduction and carrying traffic how to get Host_switch_cpu OFF?

Question: what happens if BMC --- CPU link is down ?

#### 2.1.4 BMC Leak detection and thermal policy
- Leak detected, what is the policy
- thermal sensors from Host_switch_cpu if above thresholds, what is policy 

policy can be enforced by a new daemon "bmcctld" 

### 2.2 BMC Platform Management

#### 2.2.1 BMC Monitoring and bmcctld
- New daemon which enforces policy
- it talks to local redis and host Cpu redis

#### 2.2.2 Thermalctld
- Will read leak sensor details
- Will also read the host_switch_cpu thermals
- Store in local DB

#### 2.2.3 Hw watchdog
Todo

#### 2.2.4 Platform APIs

+------------------------ Platform common Class -------------------------+
| Method / Class          | Present | Action                             |
|-------------------------|---------|-------------------------------------|

[ LeakageSensorBase ]
  get_name()              |   Y     | Get leak sensor name
  is_leak()               |   Y     | Is there a leak detected?
  get_severity()          |  New    | Get the severity of leaks

[ LiquidCoolingBase ]
  get_num_leak_sensors()  |   Y     | Get number of leak sensors
  get_leak_sensor(index)  |   Y     | Get per-leak-sensor status
  get_leak_sensor_status()|   Y     | Get all leak sensor status
  get_all_leak_sensors()  |   Y     | Get list of all leak sensors

[ BmcBase ]  --- Redfish interface CPU → BMC ---
  get_version()           |   Y     | Get BMC firmware version
  get_eeprom()            |   Y     | Get BMC EEPROM information
  get_status()            |   Y     | Get BMC status
  get_model()             |   Y     | Get BMC model
  get_serial()            |   Y     | Get BMC serial number
  update_firmware()       |   Y     | Update BMC firmware
  request_bmc_reset()     |   Y     | Do BMC reset
  ...

[ HostCpuBase ] --- Commands BMC → CPU ---
  power_on_host()         |  New    | Power on CPU board from standby/off
  power_off_host()        |  New    | Immediate HW power‑off (bypass OS)
  reboot_host()           |  New    | Graceful shutdown then power‑off
  power_cycle_host()      |  New    | Power‑cycle host CPU
  get_host_power_state()  |  New    | Fetch host power state

[ ChassisBase ]
  get_bmc()               |   Y     | Get the BMC object
  get_cpu_host()          |   Y     | Get the host CPU object

## 3 Future Items
