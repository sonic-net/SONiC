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
      * [2.2.1 BMC Monitoring and bmcctld](#221-bmc-controller---bmcctld)
        * [2.2.1.1 DB schema](#2221-db-schema)
      * [2.2.2 Thermalctld](#222-thermalctld)
        * [2.2.2.1 DB schema](#2221-db-schema)
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
BMC - Baseboard Management Controller.  
Switch-Host - Main board in network device which hosts the ASIC and CPU.  
Rack Manager - Manager module for rack where switch is mounted.  
Redfish - standard REST API for managing hardware.  
PMON - Platform Monitor. Used in the context of Platform monitoring docker/processes.  

## 1. SONiC Platform Management and Monitoring
### 1.1. Functional Requirements
This section captures the functional requirements for platform monitoring and management in sonic BMC 

* BMC can be accessed in two ways (i) via the external management interface (ii) from the Switch Host via the internal midplane ethernet interface.  
* BMC will manage the Switch Host to support operations like power up/down, get operational status.  **Question:** In Aircooled systems -- What is the role of BMC ?
* BMC will read local leak sensors and take appropriate actions based on policy. The severity of leak seansor is defined by platform via API.  
* BMC will get inputs on Inlet Liquid temperature, Inlet Liquid flow rate, Inlet Liquid Pressure,	Rack level Leak from Rack Manager. It takes action based on policy.  
* BMC can take policy action if any of the Switch Host components have temperature above critical threshold value defined in platform defenition.  
* BMC can access the Swicth Host temperature sensor data directly from redis database running on switch host.  

### 1.2. BMC Platform Stack
<Add a pic with pmon in BCM and pmon/redis in Switch-Host - via the usb interface>

## 2. Detailed Architecture and workflows
### 2.1 BMC platform
Presence of the file bmc.json in the <vendor>/platform tells this platform is either a Switch-Host or a switch_BMC. The contents of bmc.json in Switch-Host and BMC are as below.
```
Switch_Host=1
Liquid_cooled=true
```
```
Switch_BMC=1
Liquid_cooled=true
```

"Liquid_cooled" flag is set to true on a liquid cooled switch.  
"Swicth_Host" flag is set to 1 on the switch host, "Switch_BMC" flag is set to 1 on the switch BMC.   


#### 2.1.1 BMC platform power up
The BMC powers on first, boots up the sonic BMC which starts the various cointainers
If it is Aircooled network switch the Switch Host is poweron immediately. 
If it is liquid cooled, the following actions are donw before the Switch Host is powered on.
    *  "thermalctld" checks local leaks | external Leaks if any reported by Rack Manager, apply policy
    *  "bmcctld" to send a power on request to Swicth host if all clear.
<img width="556" height="725" alt="bmc_1" src="https://github.com/user-attachments/assets/9b7368e2-98cf-4467-bc68-936280f7079b" />

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
             -- Rack manager send periodic telemetry data of Inlet Liquid temperature, Inlet Liquid flow rate,
                Inlet Liquid Pressure, Leak information
    6. POST /redfish/v1/EventService/Subscriptions  
             -- Rack manager to subscribe for events like Leak from switchBMC.  

The critical Alerts from RackManagerAlert URI will be stored in local redis DB
The telemetry data from RackManagerTelemetry URI will also be stored in local redis DB to be used for thermal policy engine.

**TODO** Add reference to the redfish design doc here

#### 2.1.3 Midplane Ethernet
There is an ethernet connectivity between the Switch-Host and Switch-BMC 

The Switch-Host will intialize the usb netdev dring the inital platform bringup and name it as bmc0.
Similarly the BMC will intialize the usb netdev dring the inital platform bringup and name it as bmc-eth0

IP address to be configured on the Switch-Host end and Switch-Bmc end can be defined sonic wide unique in file "files/image_config/constants/bmc_ip_address.json" as below
```
Switch-Host=10.1.0.1
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
| UP  | Switch-Host_THERMAL_CRITICAL_EVENT | Syslog, Isolate switch, Power OFF Switch Host | DOWN 
| DOWN  | RACK_MGR_CRITICAL_EVENT & LOCAL_LEAK_NON_CRITICAL_EVENT clear | Syslog, UnIsolate switch, Power ON Switch Host | UP
| NOT REACHABLE | - | Syslog, Isolate switch, Power Cycle Switch Host | UP

**Question:** BMC Isolate/UnIsolate the switch Host before powering off
                   -- syslog wil trigger alert 
                   -- Netassisit isolate/unisolate the switch
                   -- BMC wait for the events and power off ?

#### 2.1.5 BMC Leak detection and thermal policy

**Note: This section is only applicable to Liquid cooling platform.**

thermalctld which takes input from all these below sources 

    (i) Local leak detection thread which updates leak status in LIQUID_COOLING_DEVICE|leakage_sensors{X} along with severity.  
        The result of which will set the CRITICAL/MAJOR/MINOR flag LOCAL_LEAK_CRITICAL_EVENT.  
        
    (ii) External Rack manager alert status table updated by redfish/bmcweb.  
         The result of which will set the CRITICAL/MAJOR/MINOR flag RACK_MGR_CRITICAL_EVENT.  
         
    (iii) Switch-Host thermal critical event status table.   
          - Take the various Switch-Host sensor thermals from Switch-Host redis STATE_DB.  
          - Compare it with thresholds defined in platform json.   
          
          **Question :** Do we need the liquid temperature and liquid flow rate along with thresholds ?  

### 2.2 BMC Platform Management
The daemons present in pmon would be thermalctld, syseepromd, stormond.
In Liquid cooled platforms a new daemon "bcmctld" will be introduced in pmon container.

#### 2.2.1 BMC controller - bmcctld
The bmc controller daemon "bmcctld" is started first in BMC pmon container. Its main tasks are 

(i) Power on the Switch-Host
```
Loop on this logic 
 Check if the Switch-Host is reachable and up ( case when pmon restarts )
 if YES
 {
   Check for Local Leak status + external Rack manager leak status + Switch-Host thermals status
     if CRITICAL LEAK or thermals high ( check N consecutive failures)
       syslog, POWER_OFF Switch_host, update DB SWITCH_HOST_STATE table
 }
 if NO
 {
   if it is POWERED_OFF
   {
     Check for Local Leak status + external Rack manager leak status + Switch-Host thermals status
     if NO LEAK + Switch_host thermals good ( check N consecutive success)
       syslog, POWER_ON Switch_host, update DB SWITCH_HOST_STATE table
     else
       continue
   }
   if it is First Boot
   {
     Sleep for 4 min ( this is configurable value in config_db)
     Check if the redfish connectivity with rack_manager is established ( This should be updated in redis DB by redfish docker processes)
     Check for Local Leak status + external Rack manager leak status + Switch-Host thermals status
     if NO LEAK ( check N consecutive success)
       syslog, POWER_ON Switch_host, update DB SWITCH_HOST_STATE table   
   }
 }
```

(ii) Switch-BMC and Switch-Host Heartbeat thread 
```
  Use either the redis PING/PONG, or ICMP ping req/response
  Update the "heartbeat" field in the table SWITCH_HOST_STATE
```


#### 2.2.1.1 DB schema
This section covers the various DB tables which this daemon creates/uses

```
key                                   = BMC_BOOTUP_TIMEOUT      ; Config DB
; field                               = value
boot_delay                            = float                   ; Time in secs after power on the device, switch BMC can power on the Switch-Host. ( default = 4 min ).   
                                                                ; If BMC receive POWER ON from Rack manager before this timeout + ther are no critical events - Switch-Host will be powered on
```

```
key                                   = SWITCH_HOST_STATE      ; STATE DB
; field                               = value
device_state                          = "state"                ;POWERED_ON/POWERED_OFF
heartbeat                             = "status"               ;REACHABLE/UNREACHABLE
```

#### 2.2.2 thermalctld
The thermalctld will have additional threads to do following in a liquid cooled platform

```
Thread1

Loop on this logic 
(i) Check local leak sensors using platform API and update the LOCAL_LEAK_STATUS table
(ii) Check the leak data from rack manager stored in redis DB by the redfish docker processes
        -- store the result in RACK_MGR_LEAK_STATUS table
```
```
Thread2

Loop on this logic 
(i) Get the current temperature reading from Switch-Host redis DB
(ii) Loop through the list of Switch-Host thermal sensors defined in platform.json
     {
       Compare the current temperature with the high/critical thresholds defined
     }
(iii) store the result in SWITCH_HOST_THERMAL_STATUS table

```

#### 2.2.2.1 DB schema

```
key                                   = LOCAL_LEAK_STATUS      ; STATE DB
; field                               = value
device_leak_status                    = "status"               ;CRITICAL/MAJOR/MINOR
```

```
key                                   = RACK_MGR_LEAK_STATUS      ; STATE DB
; field                               = value
rack_mgr_leak_status                  = "status"                  ;CRITICAL/MAJOR/MINOR
```

```
key                                   = SWITCH_HOST_THERMAL_STATUS      ; STATE DB
; field                               = value
switch_host_thermal_status            = "status"                        ;CRITICAL/NORMAL
```


#### 2.2.2.2 Thermal sensor thresholds in platform json
** TODO ** Define the platform.json file format where platforms can speficy the temperature threasholds for various switch-Host components.
 
#### 2.2.3 Hw watchdog
** TODO **

#### 2.2.4 Platform APIs

# Platform APIs Used

Listing down the platform common APIs planned for sonic bmc support. 

The following docs from Nvidia team which is already present define many platform API's for bmc, leak and liquidCooling

* https://github.com/sonic-net/SONiC/blob/master/doc/bmc/bmc_hld.md                                                                                                       
* https://github.com/sonic-net/SONiC/blob/master/doc/bmc/leakage_detection_hld.md 

A new base class **SwitchHostBase** is introduced along with new platform API's added to exiting base classes.

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
