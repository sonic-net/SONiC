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
        * [2.1.2.1 DB schema](#2121-db-schema)
      * [2.1.3 Host-Bmc-link](#213-host-bmc-link)
      * [2.1.4 BMC-Switch Host Interaction](#214-bmc-switch-host-interaction)
      * [2.1.5 BMC leak_detection_and_thermal policy](#215-bmc-leak-detection-and-thermal-policy)
      * [2.1.6 BMC event logging](#216-bmc-event-logging)
    * [2.2 BMC Platform Management](#22-bmc-platform-management)
      * [2.2.1 BMC controller-bmcctld](#221-bmc-controller---bmcctld)
        * [2.2.1.1 bmcctld on bmc](#2211-bmcctld-on-bmc)
        * [2.2.1.2 bmcctld on switch-host](#2212-bmcctld-on-switch-host)
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
**BMC**          - Baseboard Management Controller.  
**Switch-Host** - Main board in network device which hosts the ASIC and CPU.  
**Chassis**   - Switch-Host & BMC as a unit called chassis.  
**Rack Manager** - Manager module for rack where switch is mounted.  
**Redfish**   - standard REST API for managing hardware.  
**PMON**    - Platform Monitor. Used in the context of Platform monitoring docker/processes.  

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

![BMC Platform Stack](images/sonic-bmc-arch.png)

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

"Liquid_cooled" flag is set to true on a liquid cooled switch."Switch_Host" flag is set to 1 on the switch host, "Switch_BMC" flag is set to 1 on the switch BMC.  

In Air cooled switches this flag will not be present

#### 2.1.1 BMC platform power up
When device is powered ON, the BMC powers first, boots up the sonic BMC which starts the various cointainers   

If it is Air cooled switch the Switch-Host is powered on immediately.

If it is liquid cooled, the following actions are done before the Switch-Host is powered on.
* "thermalctld" checks local leaks and external Leaks if any reported by Rack Manager
* "bmcctld" to send a POWER_ON command to Switch-host if all clear.    

![BMC platform power up](images/sonic-bmc-bootup.png)


#### 2.1.2 BMC Rack Manager Interaction
The new docker container "redfish" in sonicBMC will have openbmc/bmcweb service which terminates the redfish calls from the rack Manager.

**Note: Redish docker to be enabled only on Liquid cooling platform.**

Few of the URIs which needs to be supported in BMC are below, please note there could be some change naming of OEM URI paths.

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

**TODO** Add reference to the redfish design doc here

#### 2.1.2.1 DB schema

Redis DB will be used to store the command/data send from external Rack manager for the platform daemons to act upon.

```
key                       = RACK_MANAGER_COMMAND|<command_id>             ; Commands from Rack Manager in STATE_DB in BMC
; field                   = value                                         ; e.g. ComputerSystem.Reset
command                   = POWER_ON | POWER_OFF | POWER_CYCLE
status                    = PENDING | ACK | DONE | FAILED

key                       = RACK_MANAGER_STATE|rack-manager               ; STATE_DB on BMC to store state of RackManager
; field                   = value
reachability              = REACHABLE | UNREACHABLE
last_change_timestamp     = STR

key                       = RACK_MANAGER_ALERT|Inlet_liquid_temperature    ; Alert data from Rack Manager in STATE_DB
; field                   = value
severity                  = "status"                                       ;CRITICAL/MINOR
timestamp                 = STR

key                       = RACK_MANAGER_ALERT|Inlet_liquid_flow_rate      ; Alert data from Rack Manager in STATE_DB
; field                   = value
severity                  = "status"                                       ;CRITICAL/MINOR
timestamp                 = STR

key                       = RACK_MANAGER_ALERT|Inlet_liquid_pressure       ; Alert data from Rack Manager in STATE_DB
; field                   = value
severity                  = "status"                                       ;CRITICAL/MINOR
timestamp                 = STR

key                       = RACK_MANAGER_ALERT|Rack_level_leak             ; Alert data from Rack Manager in STATE_DB
; field                   = value
severity                  = "status"                                       ;CRITICAL/MINOR
timestamp                 = STR
```  

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
The Switch-Host and BMC communicate over the Host-Bmc-Link for accessing redis DB.
 
Defining the various states, events and final state below

|| Switch Host (Current) | Event | Action | Switch Host (Final) 
|--|---|---|---|---|
|1| POWERED_UP  | LOCAL_LEAK_CRITICAL_EVENT | Syslog, DB update, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|2| POWERED_UP  | RACK_MGR_CRITICAL_EVENT | Syslog, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|3| POWERED_UP  | POWER OFF request | Syslog, graceful-shutdown/Power OFF Switch Host | POWERED_DOWN 
|4| POWERED_UP  | RACK_MGR_MINOR_EVENT/LOCAL_LEAK_MINOR_EVENT | Syslog | POWERED_UP
|5| POWERED_DOWN  | POWER ON request | Power ON Switch Host, Syslog | POWERED_UP

#### 2.1.5 BMC Leak detection and thermal policy

The Leak detection is applicable only to Liquid cooling platform. The action is based on alerts from two different sources 

(i) Local leak detection uses the leak status in LIQUID_COOLING_DEVICE|leakage_sensors{X}.
    The result ( whether it is critical/minor ) will be updated in LEAK_STATUS table defined in [2.2.2.1 DB schema](#2221-db-schema)
        
(ii) External Rack manager alert status is updated by redfish/bmcweb in RACK_MANAGER_ALERT table defined in [2.1.2.1 DB schema](#2121-db-schema).
    
        
#### 2.1.6 BMC event logging

The general syslogs will be placed in /var/log/syslog where /var/log directory will be mounted on **tmpfs **. Syslogs will be sent to remote server as well.
The Leak, Switch-Host state and interactions, Rack-manager interactions will be persistently stored on disk/eMMC in "/host/bmc.log" (Note: yet to conclude on exact location )

### 2.2 BMC Platform Management

The daemons present in pmon would be thermalctld, syseepromd, stormond.
In **Liquid cooled platforms** a new daemon **"bmcctld"** will be introduced in pmon container on both BMC and Switch-Host

#### 2.2.1 BMC controller - bmcctld

##### 2.2.1.1 bmcctld on BMC

The bmc controller daemon "bmcctld" is started first in BMC pmon container. The following logic is applied

```
Loop on this logic 
 Check if the Switch-Host is reachable and up ( In case when pmon/bmcctld restarts OR BMC alone restarts )
 if YES
 {
   Check if the redfish connectivity with rack_manager is established ( This should be updated in redis DB by redfish docker processes)
   Check for Local Leak status + external Rack manager leak status
     if CRITICAL LEAK
          - syslog
          - [enhancement] Try to do a soft reboot of Switch Host with a timeout of ~2min ( configurable )
          - if unsuccessfull POWER_OFF Switch_host
          - update DB SWITCH_HOST_STATE table with the status
     else
          - update DB SWITCH_HOST_STATE table with the status
 }
 if NO
 {
   if it is First Boot
   {
     Sleep for (5min - bootup time) ( this is configurable value in config_db)
   }
   Check if the redfish connectivity with rack_manager is established ( This should be updated in redis DB by redfish docker processes)
   Check for Local Leak status + external Rack manager leak status
   if NO LEAK
        - Check why is Switch-Host DOWN, is it thermal - check Switch-Host health ( How to check this ?? )
        - syslog
        - POWER_ON Switch_host if Switch-Host health ok 
        - update DB SWITCH_HOST_STATE table with status
   else
        - syslog and continue
   }
 }
```

###### DB schema
This section covers the various tables which this daemon creates/uses in Redis DB on BMC

```
key                       = BMC_BOOTUP_TIMEOUT|default         ; Config DB on BMC
; field                   = value
boot_delay                = float                              ; Time in secs after power on the device, switch BMC can power on the Switch-Host. ( default = 5 min ).   
                                                               ; If BMC receive POWER ON from Rack manager before this timeout + ther are no critical events - Switch-Host will be powered on

key                       = HOST_STATE|switch-host             ; STATE_DB on BMC to store state of Switch-Host
; field                   = value
device_power              = POWERED_ON | POWERED_OFF
reachability              = REACHABLE | UNREACHABLE
last_change_timestamp     = STR

key                       = SWITCH_HOST_REBOOT_TIMEOUT|default ; Config DB on BMC
; field                   = value
shutdown_delay            = float                              ; Time in secs the BMC will wait after REBOOT command issued to Switch-Host. ( default = 2 min ).
                                                               ; if this timer expires, BMC will go ahead and POWER OFF switch-host

```

##### 2.2.1.2 bmcctld on Switch-Host

The bmcctld daemon on the Switch-Host will subscribe to STATE DB table "BMC_TO_SWITCH_HOST_CMD" for any shutdown/reboot command from BMC.
On receipt of this event, the Switch-Host will be shutdown/reboot gracefully.

###### DB schema
This section covers the various tables which this daemon creates/uses in Redis DB on BMC
Below DB tables are enhancements to help support graceful reboot of Switch-Host before doing a power off, with a timeout configured in SWITCH_HOST_SHUT_TIMEOUT.
We would need an instance of bmcctld running on Switch-Host as well to subscribe to these tables.

**Note: ** Still to validate if we need this infra to do a gracefull shutdown

```
key                       = BMC_TO_SWITCH_HOST_COMMAND|<command_id>   ; STATE_DB on Switch-Host
; field                   = value
command                   = SHUTDOWN | REBOOT                         ; shutdown or soft reboot the Switch-Host
reason                    = STR                                       ; optional reason string

key                       = BMC_STATE|bmc                             ; STATE_DB on Switch-Host to store state of BMC
; field                   = value
reachability              = REACHABLE | UNREACHABLE
last_change_timestamp     = STR
```

#### 2.2.2 thermalctld
In Liquid cooled platform, thermalctld will skip the PSU, FAN, SFP thermals but have additional responsibilities to check leak sensors and apply leak policy.

```
Loop on this logic 
  (i) Check local leak sensors using platform API
         -- store the result in LIQUID_COOLING_DEVICE table
         -- Leak severity can either be CRITICAL or MINOR

  (ii) Apply the thermal policy based on the number and severity of leak sensors with leak
       
       +--------------------------------------+-----------------------+
       | Leak conditions                      | System Leak Severity  |
       +--------------------------------------+-----------------------+
       | 1 or more (Critical) leaks           |        CRITICAL       |
       | 2 or more leaks with any Severity    |        CRITICAL       |
       | 1 (Minor) leak stay leaking for MAX-T|        CRITICAL       |
       | 1 (Minor) leak detected              |        MINOR          |
       +--------------------------------------+-----------------------+

       Additional considerations:
         - MAX-T mins defined before which a Minor leak can be considered CRITICAL need to be tested, Should it be per platform ?
         - Need to apply debounce timers
             (i) debounce_assert_sec : A leak must remain continuously detected for this much time to be trated as real leak
             (ii) debounce_clear_sec : Once a leak clears, it must remain clear for this much time before the system considers it resolved.

   (iii) Update the local LEAK_STATUS table with the severity of leak. This will be used in bmcctld process.

```
 
#### 2.2.2.1 DB schema

This LIQUID_COOLING_DEVICE table is already populated by thermalctld. New field **severity ** is introduced.
```
key                       = LIQUID_COOLING_DEVICE|leakage_sensors{X}  ; leak data in STATE_DB per sensor
 ; field                  = value
name                      = STR                                       ; sensor name
leaking                   = STR                                       ; Yes or No to indicate leakage status
severity                  = "status"                                  ;CRITICAL/MINOR

key                       = LEAK_STATUS|local                         ; local bmc leak status in STATE DB
; field                   = value
device_leak_status        = "status"                                  ;CRITICAL/MINOR
```     

#### 2.2.3 Hw watchdog
Hw watchdog timers will be enabled on both Switch-Host and BMC. 
This will do a CPU reset when OS hangs or becomes unresponsive and fails to service the watchdog

#### 2.2.4 Platform APIs

# Platform APIs Used

Listing down the platform common APIs planned for sonic bmc support. 

The following docs from Nvidia team which is already present define many platform API's for bmc, leak and liquidCooling

* https://github.com/sonic-net/SONiC/blob/master/doc/bmc/bmc_hld.md                                                                                                       
* https://github.com/sonic-net/SONiC/blob/master/doc/bmc/leakage_detection_hld.md 

A new base class **SwitchHostBase** is introduced along with new platform API's added to exiting base classes.

####  LeakageSensorBase
This base class is already defined in sonic-platform-common. 
 - Adding a new API get_severity() which retuns back the severity of a particular leak

| Method | Present | Action |
|---------|---------|----------|
| get_name() | Y | Get leak sensor name |
| is_leak() | Y | Is there a leak detected? |
| get_severity() | New | Get the severity based on the criticality of the zone |

---

#### LiquidCoolingBase
This base class is already defined in sonic-platform-common. 

| Method | Present | Action |
|---------|---------|----------|
| get_num_leak_sensors() | Y | Get number of leak sensors |
| get_leak_sensor(index) | Y | Get per-leak-sensor status |
| get_leak_sensor_status() | Y | Get all leak sensor status |
| get_all_leak_sensors() | Y | Get list of all leak sensors |

---

####  BmcBase
This base class is already defined in sonic-platform-common. 

This Class contains API's for Switch-Host to control the switch BMC, In the current implementation Calls from Switch-Host --> BMC uses redfish.
**We need to change this class to have flexibility to either use Redis DB or Redfish**

| Method | Present | Action |
|---------|---------|----------|
| get_version() | Y | Get BMC firmware version |
| get_eeprom() | Y | Get BMC EEPROM information |
| get_status() | Y | Get BMC status |
| get_model() | Y | Get BMC model |
| get_serial() | Y | Get BMC serial number |

---

####  SwitchHostBase
This Class is a new BaseClass to define which will contain API's for switch BMC to control the Switch-Host

| Method | Present | Action |
|---------|---------|----------|
| power_on_switch_host() | New | Power on Switch Host from standby/off |
| power_off_switch_host() | New | Immediate HW power-off (bypass OS) |
| reboot_switch_host() | New | Graceful shutdown of Switch Host|
| power_cycle_switch_host() | New | Power-cycle Switch Host |
| get_switch_host_power_state() | New | Fetch Switch host power state |
| get_switch_host_health() | New | Fetch Switch host health like thermal, power  ** to be decided ** |

---

####  ChassisBase
This base class is already defined in sonic-platform-common. We need a new API get_switch_host().

| Method | Present | Action |
|---------|---------|----------|
| get_bmc() | Y | Get the BMC object |
| get_switch_host() | New | Get the Switch Host object |

### 2.2 BMC CLI Commands
Following commands are enhanced to support BMC operation

#### Config commands

1. CLI to enable user to powercycle/reboot the Switch-Host
```
config chassis modules startup <Switch-Host>
config chassis modules shutdown <Switch-Host>
config chassis modules reboot <Switch-Host>
```

#### Show commands 

```
admin@bmc-host:~$ show chassis module status
        Name             Description    Oper-Status    Admin-Status       Serial
------------  ----------------------  -------------  --------------  -----------
BMC            Board Management Card         Online              up           <>
Switch-Host     <Device sku details>         Online              up           <>

```

## 3 Future Items
