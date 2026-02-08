# SONiC BMC Platform Management & Monitoring #

# Table of Contents

  * [Revision](#revision)
  * [Scope](#scope)
  * [Acronyms](#acronyms)
  * [1. SONiC Platform Management and Monitoring](#1-sonic-platform-management-and-monitoring)
    * [1.1 Functional Requirements](#11-functional-requirements)
    * [1.2 BMC Platform Stack](#12-bmc-platform-stack)
  * [2. Detailed Architecture and Workflows](#2-detailed-architecture-and-workflows)
    * [2.1 BMC Platform](#21-bmc-platform)
      * [2.1.1 BMC platform power up](#211-bmc-platform-power-up) 
      * [2.1.2 BMC Rack Manager Interaction](#212-bmc-rack-manager-interaction)
      * [2.1.3 Midplane Ethernet](#213-midplane-ethernet)
      * [2.1.4 BMC-Swicth Host Interaction](#214-bmc-switch-host-interaction)
      * [2.1.5 BMC leak_detection_and_thermal policy](#215-bmc-leak-detection-and-thermal-policy)      
    * [2.2 BMC Platform Management](#22-bmc-platform-management)
      * [2.2.1 BMC Monitoring and bmcctld](#221-bmc-monitoring-and-bmcctld)
        * [2.2.1.1 DB schema changes](#2211-db-schema-changes)
      * [2.2.2 Thermalctld](#222-thermalctld)
        * [2.2.2.1 DB schema changes](#2221-db-schema-changes)
        * [2.2.2.2 Thermal sensor thresholds in platform json](#2222-thermal-sensor-thresholds-in-platform-json)      
      * [2.2.3 Hw watchdog](#223-hw-watchdog)
      * [2.2.4 Platform APIs](#224-platform-apis)
  * [3 Future Items](#3-future-items)

      
### Revision ###

 | Rev |     Date    |       Author                                                            | Change Description                |
 |:---:|:-----------:|:-----------------------------------------------------------------------:|-----------------------------------|
 | 1.0 |             |                                                                         | Initial version                   |

# Scope
This document provides design requirements and interactions between platform drivers and PMON for SONiC on BMC 

# Acronyms
BMC - Baseboard Management Controller
Swicth-Host - Main board in network device which hosts the ASIC and CPU
Rack Manager - Manager module for rack where switch is mounted.
Redfish - standard REST API for managing hardware
PMON - Platform Monitor. Used in the context of Platform monitoring docker/processes.

## 1. SONiC Platform Management and Monitoring
### 1.1. Functional Requirements
This section captures the functional requirements for platform monitoring and management in sonic BMC 

* BMC can be accessed in two ways (i) via the external management interface (ii) from the Switch Host via the internal midplane ethernet interface.
* BMC will manage the Switch Host to support operations like power up/down, get operational status.
* BMC will read local leak sensors and take appropriate actions based on policy. The severity of leak seansor is defined by platform via API
* BMC will get inputs on Inlet Liquid temperature, Inlet Liquid flow rate, Inlet Liquid Pressure,	Rack level Leak from Rack Manager. It takes action based on policy
* BMC can take policy action if any of the Switch Host components have temperature above critical threshold value defined in platform defenition.
* BMC can access the Swicth Host temperature sensor data directly from redis database running on switch host.

### 1.2. BMC Platform Stack
<Add a pic with pmon in BCM and pmon/redis in switch_host - via the usb interface>

## 2. Detailed Architecture and workflows
### 2.1 BMC platform
Presence of the file bmc.json in the <vendor>/platform tells this platform is either a Switch_Host or a switch_BMC. The contents of bmc.json can be as below 
```
Swicth_Host=1
```
```
Switch_BMC=1
```
#### 2.1.1 BMC platform power up
The BMC powers on first, boots up the sonic BMC which starts the various cointainers
If it is Aircooled network switch the Switch Host is poweron immediately. 
If it is liquid cooled, the following actions are donw before the Switch Host is powered on.
*  "thermalctld" checks local leaks | external Leaks if any reported by Rack Manager, apply policy
*  "bmcctld" to send a power on request to Swicth host if all clear.
<img width="556" height="725" alt="bmc_1" src="https://github.com/user-attachments/assets/6fc9d0a5-e49f-4899-9d9c-2b284b35db98" />

#### 2.1.2 BMC Rack Manager Interaction
The new docker container "redfish" in sonicBMC will have openbmc/bmcweb service which terminates the redfish calls from the rack Manager.

**Note: Redish docker to be enabled only on Liquid cooling platform.**

Few of the URIs which needs to be supported in BMC are (there could be some change to OEM URI)
Not all below URI is applicable to Air cooled switch.

1. GET /redfish/v1   
         -- Rack Manager to get switch name
2. GET /redfish/v1/UpdateService/FirmwareInventory  
         -- Rack Manager to get switch firmware details
3. POST /redfish/v1/Systems/System/Actions/ComputerSystem.Reset  
         -- Rack Manager to power off/on Main_cpu_switch_board
4. POST /redfish/v1/Managers/Bmc/Actions/Oem/SONiC.RackManagerAlert  
         -- Rack manager to post a critical alert to BMC
5. POST /redfish/v1/Managers/Bmc/Actions/Oem/SONiC.RackManagerTelemetry  
         -- Rack manager send periodic telemetry data of Inlet Liquid temperature, Inlet Liquid flow rate, Inlet Liquid Pressure, Leak information
6. POST /redfish/v1/EventService/Subscriptions  
         -- Rack manager to subscribe for events like Leak from switchBMC (P1 feature)

The critical Alerts from RackManagerAlert URI will be stored in local redis DB
The telemetry data from RackManagerTelemetry URI will also be stored in local redis DB to be used for thermal policy engine.

**TODO** Add reference to the redfish design doc here

#### 2.1.3 Midplane Ethernet

The Switch_Host will intialize the usb netdev dring the inital platform bringup and name it as bmc0.
Similarly the BMC will intialize the usb netdev dring the inital platform bringup and name it as bmc-eth0

IP address to be configured on that the Switch_host end and Bmc end will be defined in file "files/image_config/constants/bmc_ip_address.json" as below
```
Switch_Host=10.1.0.1
Switch_BMC=10.1.0.2
```

#### 2.1.4 BMC-Switch Host Interaction
The switch Host and switch BMC communicate over the midplane ethernet for the following 
  (i) Redis database access.
  (ii) switch BMC can have a heartbeat mechanishm ( either redis PING/PONG, or ICM Echo/reply). 
  (iii) power ON/OFF the Switch Host on critical errors (** only in the Liquid cooling platform **)
  
Defining the various states, events and final state below

| Switch Host (Current) | Event | Action | Switch Host (Final) 
|---|---|---|---|
| UP  | RACK_MGR_CRITICAL_EVENT/LOCAL_LEAK_CRITICAL_EVENT | Syslog, Isolate switch, Power OFF Switch Host | DOWN 
| UP | RACK_MGR_NON_CRITICAL_EVENT/LOCAL_LEAK_NON_CRITICAL_EVENT | Syslog | UP
| UP  | SWITCH_HOST_THERMAL_CRITICAL_EVENT | Syslog, Isolate switch, Power OFF Switch Host | DOWN 
| DOWN  | RACK_MGR_CRITICAL_EVENT & LOCAL_LEAK_NON_CRITICAL_EVENT clear | Syslog, UnIsolate switch, Power ON Switch Host | UP
| NOT REACHABLE | - | Syslog, Isolate switch, Power Cycle Switch Host | UP

**Question:** BMC Isolate/UnIsolate the switch Host before powering off
                   -- syslog wil trigger alert 
                   -- Netassisit isolate/unisolate the switch
                   -- BMC wait for the events and power off ?

#### 2.1.5 BMC Leak detection and thermal policy

**Note: This section is only applicable to Liquid cooling platform.**

A new thermal policy engine thread will be introduced in thermalctld which takes input from all these below sources 

   (i) Local leak detection thread which updates leak status in LIQUID_COOLING_DEVICE|leakage_sensors{X} along with severity.
       The result of which will set the CRITICAL/MAJOR/MINOR flag LOCAL_LEAK_CRITICAL_EVENT
   (ii) External Rack manager alert status table updated by redfish/bmcweb.
        The result of which will set the CRITICAL/MAJOR/MINOR flag RACK_MGR_CRITICAL_EVENT
   (iii) Switch_Host thermal critical event status table 
         - Take the various Switch_Host sensor thermals from Switch_Host redis STATE_DB
         - Compare it with thresholds defined in platform json 
         - **Question :** We need the liquid temperature and liquid flow rate along with threadholds ?

### 2.2 BMC Platform Management

#### 2.2.1 BMC Monitoring and bmcctld
- New daemon which enforces policy
- it talks to local redis and Switch Host redis

#### 2.2.1.1 DB schema changes
New table 
  - Swicth Host state



#### 2.2.2 Thermalctld
- Will read leak sensor details
- Will also read the host_switch_cpu thermals
- Store in local DB

#### 2.2.2.1 DB schema changes



#### 2.2.2.2 Thermal sensor thresholds in platform json


#### 2.2.3 Hw watchdog
** TODO **

#### 2.2.4 Platform APIs

# Platform APIs Used

Listing down the platform common APIs planned for sonic bmc support. 

The following docs from Nvidia team which is already present define many platform API's for bmc, leak and liquidCooling

https://github.com/sonic-net/SONiC/blob/master/doc/bmc/bmc_hld.md                                                                                                       
https://github.com/sonic-net/SONiC/blob/master/doc/bmc/leakage_detection_hld.md 

There are a few new API's which needs to be added in few of the below base classes.

###  LeakageSensorBase

| Method | Present | Action |
|---------|---------|----------|
| get_name() | Y | Get leak sensor name |
| is_leak() | Y | Is there a leak detected? |
| get_severity() | New | Get the severity of leaks |

---

###  LiquidCoolingBase

| Method | Present | Action |
|---------|---------|----------|
| get_num_leak_sensors() | Y | Get number of leak sensors |
| get_leak_sensor(index) | Y | Get per-leak-sensor status |
| get_leak_sensor_status() | Y | Get all leak sensor status |
| get_all_leak_sensors() | Y | Get list of all leak sensors |

---

###  BmcBase — Redfish Interface (CPU → BMC)
This Class contains API's for switch Host to control the switch BMC

| Method | Present | Action |
|---------|---------|----------|
| get_version() | Y | Get BMC firmware version |
| get_eeprom() | Y | Get BMC EEPROM information |
| get_status() | Y | Get BMC status |
| get_model() | Y | Get BMC model |
| get_serial() | Y | Get BMC serial number |

---

###  SwitchHostBase
This Class contains API's for switch BMC to control the switch Host

| Method | Present | Action |
|---------|---------|----------|
| power_on_host() | New | Power on CPU board from standby/off |
| power_off_host() | New | Immediate HW power-off (bypass OS) |
| reboot_host() | New | Graceful shutdown then power-off |
| power_cycle_host() | New | Power-cycle Switch Host |
| get_host_power_state() | New | Fetch host power state |

---

###  ChassisBase

| Method | Present | Action |
|---------|---------|----------|
| get_bmc() | Y | Get the BMC object |
| get_cpu_host() | New | Get the Switch Host object |



## 3 Future Items
