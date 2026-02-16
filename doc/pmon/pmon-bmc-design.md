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
      * [2.1.3 Host-Bmc-link](#213-host-bmc-link)
      * [2.1.4 BMC-Switch Host Interaction](#214-bmc-switch-host-interaction)
      * [2.1.5 BMC leak_detection_and_thermal policy](#215-bmc-leak-detection-and-thermal-policy)
      * [2.1.6 BMC event logging](#216-bmc-event-logging)
    * [2.2 BMC Platform Management](#22-bmc-platform-management)
      * [2.2.1 BMC controller-bmcctld](#221-bmc-controller---bmcctld)
        * [2.2.1.1 DB schema](#2221-db-schema)
      * [2.2.2 Thermalctld](#222-thermalctld)
        * [2.2.2.1 DB schema](#2221-db-schema)        
      * [2.2.3 Hw watchdog](#223-hw-watchdog)
      * [2.2.4 Platform APIs](#224-platform-apis)
    * [2.3 BMC CLI Commands](#22-bmc-cli-commands)
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
Chassis - Swicth-Host + BMC as a unit called chassis.
Rack Manager - Manager module for rack where switch is mounted.  
Redfish - standard REST API for managing hardware.  
PMON - Platform Monitor. Used in the context of Platform monitoring docker/processes.  

## 1. SONiC Platform Management and Monitoring
### 1.1. Functional Requirements
This section captures the functional requirements for platform monitoring and management in sonic BMC 

* BMC can be accessed in two ways (i) via the external management interface (ii) from the Switch Host via the internal Host-Bmc-Link
* BMC can access Switch-Host redis DB over this internal Host-Bmc-Link.
* BMC will manage the Switch Host to support operations like soft reboot, power up/down, get operational status.  
* BMC will read local leak sensors, its severity and take appropriate actions based on policy.
* BMC will get inputs from external Rack Manager on Inlet Liquid temperature, Inlet Liquid flow rate, Inlet Liquid Pressure and Rack level Leak. It takes action based on policy.  
* BMC and Switch-Host shall each enable an independent Hw watchdog timer.
  
* Switch-Host can access BMC redis DB over this internal Host-Bmc-Link.
* Switch-Host will manage its thermal sensors and automatically power down when any thermal sensor temperature exceeds the policy-defined thresholds.
    
### 1.2. BMC Platform Stack

<Add a pic with pmon in BCM and pmon/redis in Switch-Host - via the usb interface>

## 2. Detailed Architecture and workflows
### 2.1 BMC platform
Presence of the file bmc.json in the vendor/platform directory tells this platform has BMC. The contents of bmc.json in Switch-Host and BMC are as below.
```
Switch_Host=1
Liquid_cooled=true
```
```
Switch_BMC=1
Liquid_cooled=true
```

"Liquid_cooled" flag is set to true on a liquid cooled switch. In Air cooled switches this flag will not be present
"Swicth_Host" flag is set to 1 on the switch host, "Switch_BMC" flag is set to 1 on the switch BMC.   

#### 2.1.1 BMC platform power up
When device is powered ON, the BMC powers first, boots up the sonic BMC which starts the various cointainers   

If it is Air cooled switch the Switch Host is powered on immediately.

If it is liquid cooled, the following actions are done before the Switch Host is powered on.
* "thermalctld" checks local leaks and external Leaks if any reported by Rack Manager
* "bmcctld" to send a power on request to Swicth host if all clear.    
    
<img width="556" height="725" alt="bmc_bootup" src="https://github.com/user-attachments/assets/28f21964-8efb-4ebe-a092-7fc1415d067e" />


#### 2.1.2 BMC Rack Manager Interaction
The new docker container "redfish" in sonicBMC will have openbmc/bmcweb service which terminates the redfish calls from the rack Manager.

**Note: Redish docker to be enabled only on Liquid cooling platform.**

Few of the URIs which needs to be supported in BMC are (there could be some change to OEM URI)
Not all below URI is applicable to Air cooled switch.

    1. GET /redfish/v1   
             -- Rack Manager to get switchBMC type eg: "SONiCBMC"
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

#### 2.1.3 Host-Bmc-Link
There is ethernet link between the Switch-Host and Switch-BMC ( eg: Ethernet over USB )

The Switch-Host will intialize the usb netdev dring the inital platform bringup and name it as bmc0.
Similarly the BMC will intialize the usb netdev dring the inital platform bringup and name it as bmc-eth0

IP address to be configured on the Switch-Host end and Switch-Bmc end can be defined sonic wide unique in file "files/image_config/constants/bmc_ip_address.json" as below
```
Switch_Host=169.254.100.1
Switch_BMC=169.254.100.2
```

#### 2.1.4 BMC-Switch Host Interaction
The Switch-Host and BMC communicate over the Host-Bmc-Link for accessing redis DBs for gathering sensor data.
 
Defining the various states, events and final state below

|| Switch Host (Current) | Event | Action | Switch Host (Final) 
|--|---|---|---|---|
|1| POWERED_UP  | LOCAL_LEAK_CRITICAL_EVENT | Syslog, DB update, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|2| POWERED_UP  | RACK_MGR_CRITICAL_EVENT | Syslog, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|3| POWERED_UP  | POWER OFF request | Syslog, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|4| POWERED_UP  | RACK_MGR_MINOR_EVENT/LOCAL_LEAK_MINOR_EVENT | Syslog | POWERED_UP
|5| POWERED_DOWN  | POWER ON request | Power ON Switch Host, Syslog | POWERED_UP

#### 2.1.5 BMC Leak detection and thermal policy

The Leak detection is applicable only to Liquid cooling platform. The thermalctld which takes input from all these below sources 

    (i) Local leak detection task which updates leak status in LIQUID_COOLING_DEVICE|leakage_sensors{X} along **with severity**.  
        The result of which will set the CRITICAL/MAJOR/MINOR flag in LOCAL_LEAK_EVENT_TABLE in STATE_DB
        
    (ii) External Rack manager alert status table updated by redfish/bmcweb.  
         The result of which will set the CRITICAL/MAJOR/MINOR flag in RACK_MGR_EVENT_TABLE in STATE_DB

The "bmcctld" daemon on BMC will act on these events based on action defined in [2.1.4 BMC-Switch Host Interaction](#214-bmc-switch-host-interaction)
         
#### 2.1.6 BMC event logging
The general syslogs will be placed in syslog where /var/log will be mounted on tmpfs partition and send to remote rsyslog server
The Leak, Switch-Host state and interactions, Rack-manager interactions will be stored on disk/eMMC in "/var/log/bmc.log"

### 2.2 BMC Platform Management
The daemons present in pmon would be thermalctld, syseepromd, stormond.
In Liquid cooled platforms a new daemon "bcmctld" will be introduced in pmon container on both BMC and Switch-Host

#### 2.2.1 BMC controller - bmcctld

##### bmcctld on BMC

The bmc controller daemon "bmcctld" is started first in BMC pmon container. Its main tasks are 

(i) Power on the Switch-Host
```
Loop on this logic 
 Check if the Switch-Host is reachable and up ( case when pmon restarts )
 if YES
 {
   Check for Local Leak status + external Rack manager leak status + Switch-Host thermals status
     if CRITICAL LEAK or thermals high ( check N consecutive failures)
       - syslog
       - Try to do a soft reboot of Switch Host with a timeout of ~2min ( configurable )
       - if unsuccessfull POWER_OFF Switch_host
       - update DB SWITCH_HOST_STATE table with the status
 }
 if NO
 {
   if it is First Boot
   {
     Sleep for 5 min ( this is configurable value in config_db)
     Check if the redfish connectivity with rack_manager is established ( This should be updated in redis DB by redfish docker processes)
     Check for Local Leak status + external Rack manager leak status
     if NO LEAK
       - syslog
       - POWER_ON Switch_host
       - update DB SWITCH_HOST_STATE table with status 
   }
 }
```

##### bmcctld on Switch-Host

The bmc controller daemon on the Switch-Host will subscribe to STATE DB table "BMC_TO_SWITCH_HOST_CMD" for any shutdown/reboot command from BMC.
On receipt of this event, the Switch-Host will be shutdown/reboot gracefully.

#### 2.2.1.1 DB schema
This section covers the various DB tables which this daemon creates/uses

```
key                                   = BMC_BOOTUP_TIMEOUT      ; Config DB on BMC
; field                               = value
boot_delay                            = float                   ; Time in secs after power on the device, switch BMC can power on the Switch-Host. ( default = 4 min ).   
                                                                ; If BMC receive POWER ON from Rack manager before this timeout + ther are no critical events - Switch-Host will be powered on
```

```
key                                   = SWITCH_HOST_STATE      ; STATE DB on BMC
; field                               = value
device_state                          = "state"                ;POWERED_ON/POWERED_OFF
device_status                         = "status"               ;REACHABLE/UNREACHABLE
```

```
key                                   = BMC_TO_SWITCH_HOST_CMD     ; CONFIG_DB on Switch-Host
; field                               = value
command                               = "SHUTDOWN/REBOOT"          ; shutdown/soft reboot the Switch-Host
```

```
key                                   = SWITCH_HOST_SHUT_TIMEOUT   ; Config DB on BMC
; field                               = value
shutdown_delay                        = float                      ; Time in secs after SHUT command issued to Switch-Host should BMC do POWER OFF. ( default = 2 min ).
```

#### 2.2.2 thermalctld
The thermalctld will have an additional thread to do following in a liquid cooled platform

```

Loop on this logic 
(i) Check local leak sensors using platform API
        -- store the result in LOCAL_LEAK_STATUS table
(ii) Check the leak data from rack manager stored in redis DB by the redfish docker processes
        -- store the result in RACK_MGR_LEAK_STATUS table
```

#### 2.2.2.1 DB schema

```
key                                   = LOCAL_LEAK_STATUS      ; STATE DB
; field                               = value
device_leak_status                    = "status"               ;CRITICAL/MAJOR/MINOR
device_leak_sensor                    = "sensor_name"          ; leak sensor which is flagged critical 
```

```
key                                   = RACK_MGR_LEAK_STATUS      ; STATE DB
; field                               = value
rack_mgr_leak_status                  = "status"                  ;CRITICAL/MAJOR/MINOR
device_leak_sensor                    = "sensor_name"             ; leak sensor which is flagged critical
```

#### 2.2.3 Hw watchdog
Hw watchdog timers will be enabled on both Switch-Host and BMC to reboot on software hugh issues.

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
In the current implementation Calls from switch Host --> BMC uses redfish. **We need to change this class to have flexibility to either use Redis DB or Redfish**

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
| power_on_switch_host() | New | Power on Switch Host from standby/off |
| power_off_switch_host() | New | Immediate HW power-off (bypass OS) |
| reboot_switch_host() | New | Graceful shutdown of Switch Host|
| power_cycle_switch_host() | New | Power-cycle Switch Host |
| get_switch_host_power_state() | New | Fetch Switch host power state |

---

###  ChassisBase

| Method | Present | Action |
|---------|---------|----------|
| get_bmc() | Y | Get the BMC object |
| get_switch_host() | New | Get the Switch Host object |

### 2.2 BMC CLI Commands





## 3 Future Items
