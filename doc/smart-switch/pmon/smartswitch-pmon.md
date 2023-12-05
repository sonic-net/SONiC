# SmartSwitch PMON High Level Design

| Rev | Date | Author | Change Description |
| --- | ---- | ------ | ------------------ |
| 0.1 | 12/02/2023 | Ramesh Raghupathy | Initial version| 

## Definitions / Abbreviations

| Term | Meaning |
| --- | ---- |
| PMON | Platform Monitor |
| DLM | Device Lifecycle Manager |
| NPU | Network Processing Unit |
| DPU | Data Processing Unit |
| PDK | Platform Development Kit |
| SAI | Switch Abstraction Interface |
| GPIO | General Purpose Input Output |
| PSU | Power Supply Unit |
| I2C | Inter-integrated Circuit communication protocol |
| SysFS | Virtual File System provided by the Linux Kernel |
| CP | Control Plane |
| DP | Data Plane |
| SLED | Single Large Extender Device, DPU Card |

## 1. Background
SmartSwitch offloads the Packet Processors (NPUs) and the host CPUs, freeing up resources for application performance, thereby performing layer four to layer seven functions in a cost effective and space saving way. 

The specialized DPUs when built into a regular switch, can provide such a capability, which is being referred as SmartSwitch.
Platform monitor PMON in SONiC is a container responsible for chassis management functions to ensure proper operation of the devices and peripherals in the chassis there by ensuring the proper operation of the product. 

The typical lifecycle of a product involves the following stages.

<p align="center"><img src="./images/lifecycle.svg"></p>

The following sub-tasks are performed under each stage
* Onboarding
    * Boot, Shutdown, Power Cycle
    * Rest, PCIe-Reset
* Monitoring
    * Device State (dpu_state)
    * Sensors, PSUs, Colling Devices, Thermal management
    * Show CLIs
* Detection and Debugging
    * DPU Health
    * Alarms, Syslog
    * Console
* RMA
    * Inventory

The purpose of this document is to provide a framework to share the state, health, alarms of the DPUs, manage the DPUs by providing support to monitor, gracefully shutdown, restart them and the associated peripherals such as thermal sensors, cooling devices, LEDs, etc.

The picture below highlights the PMON vertical and its association with other logics within the SONiC architecture.

<p align="center"><img src="./images/pmon-vertical.svg"></p>

## 2.	Requirements, Assumptions and SLA
### 2.1.    Onboarding
* The SmartSwitch host PMON should be able to Power Cycle, Shutdown, Reset, and rest the PCIe link per DPU or the entire system
* The DPU must provide additional information such as reboot cause, timestamp, etc as explained in the scheme once it boots its OS to DPU_STATE table.
* When the DPU reboots itself, should log the reboot cause and update the previous-reboot-cause-dpu field in the ChassisStateDB when it boots up again
* When the SmartSwitch host reboots the DPU, the host should update the previous-reboot-cause-host field in the ChassisStateDB
* The reboot-cause history should provide a holistic view of the reboot cause of the SmartSwitch host CPU, the reboot-cause of all the DPUs as seen by the Switch and the DPU itself.
* The DPUs should be uniquely identified (See DPU-ID IP/MAC allocation table) and the DPU upon boot should get this ID from the host and identify itself.
* The DPU-ID itself can be used to assign the IP address of the midplane interface for both end points of the midplane interface between the host and dpu (see the midplane-interface  IP address assignment section)
* Implement the required new APIs for DPU management (see details in design section)
* SmartSwitch should use the existing SONiC midplane-interface model in modular chassis design for communication between the DPU and the NPU
* SmartSwitch should extend the SONiC modular chassis design and treat the dpu-cards (SLED) just like line-cards in existing design
* Reboot
    * Only cold reboot of DPUs is required, warm boot support is not required.
### 2.2. Monitoring and Thermal Management
* Dpu State
    * The DPUs should provide their state to the host as the boot progression happens, through the host hardware (see the DPU state table for details)
    * SmartSwitch should store the dpu state data in the DPU_STATE table in the host ChassisStateDB (explained in DB schema)
    * DPUs should be able to store the data using a redis call
    * The DPU must provide additional information on the state once it boots its OS to DPU_STATE table.
    * The SmartSwitch host PMON should be able to monitor the liveliness of the DPUs and when they go down should be able to take appropriate actions such as updating the state of the DPU in the DB and should try to gracefully recover the DPU when requested by the PMON

* Thermal management
    * Sensor values and fan speeds, status should be read periodically and stored in SmartSwitch StateDB
    * Platform modules should use this thermal sensor values against the thresholds in the thermal policy and adjust fan speeds depending on the temperature
    * Trigger thermal shut down on critical policy violation

* Show CLIs
    * Extend existing CLIs such as show platform fan/temperature to support the new HW
    * Add new CLIs 
        ```
        show dpu <id> state
        ```
### 2.3. Detect and Debug
* Health
    * SmartSwitch DPUs should store their health data in their local StateDB 
    * DPUs should support a CLI to display the health data “show dpu health”
    * The host should be able to access this data using a redis call or an api
* Alarm and Syslog
    * Raise alarms when the temperature thresholds exceed, fans run slow or not present or faulty
    * Drive LEDs accordingly
    * Provide LED status indicators for DPU boards
    * Trigger syslog
* Console
    * Provide console access to the DPUs through the Host CPU from the front panel management port
### 2.3. RMA
* The dpu-cards should be displayed as part of inventory
* Extend the CLI “show platform inventory” to display the dpu-cards and their state
* The system should be powered down for replacement of dpu-card (SLED)

## 3.	SmartSwitch PMON Design
SmartSwitch PMON block diagram
<p align="center"><img src="./images/pmon-blk-dgm.svg"></p>

### 3.1. Platform monitoring and management
* SmartSwitch design Extends the existing chassid
* Extend chassisd for dpu and add dpu-crad as a module besides the existing rp, lc, fc
* Abstract dpu-card (SLED) for higher level constructs as needed (Ex: Provide APIs at DPU level shown below)
* changes to platform plugin
    * extend module.py to support dpu module
        * class DpuCardModule(Module):
    * Update the DPU_STATE table information read from platform (refer DB schema section)
    * Once DPU boots it will update the remaining DPU_STATE information in the SmartSwitch ChassisStateDB
* APIs
    * Existing APIs: get_name, get_type, get_my_slot_idx, etc
    * New APIs
        * get_dpu_state,  (will take dpu ID or slot/offset as an argument)
        * get_dpu_health, (will take dpu ID or slot/offset as an argument)
        * get_dpu_id, (will slot/offset as an argument)
        * get_dpu_ip, (will take dpu ID or slot/offset as an argument)
        * get_dpu_mac (will take dpu ID or slot/offset as an argument)
    * Update sensor, peripheral device date to sysfs, state-DB/ChassisStateDB (platform-DB)

### 3.1. Thermal management
* Platform  initializes all sensors
* Thermalctld fetch CPU temperature, DPU temperature, fan speed, monitor and update the DB
* Thermal manager reads all thermal sensor data, run thermal policy and take policy action Ex. Set fan speed, set alarm, set syslog, set LEDs 
* Platform collects fan related data such as presence, failure and then applies fan algorithm to set the new fan speed
* The north bound CLI/Utils/App use DB data to ”show environment”, ”show platform temp” show platform fan”

Thermal management sequence diagram
<p align="center"><img src="./images/thermal-mgmt-seq.svg"></p>

### 3.2. Platform device data collection 
* thermalcontrold, led and PSUd post device data to DB periodically
* during the boot up of the daemons, it will collect the constant data like serial number, manufacture name, etc.
* For the variable ones (temperature, voltage, fan speed ....) need to be collected periodically. 

### 3.3. DPU STATE
* DPU state represents the various operational states of the DPU. They are: Powered, PCIe-Link, Host-DPU Eth-Link, Firmware, OS, CP, DP.
* The table below shows the various DPU states, the producer and consumers of them.
#### 3.3.1. DPU_STATE - Before DPU OS boots
* All DPU States are updated by the Host PMON
* These states are available to host PMON as register bits from DPUs.
* Additionally, the FPGA provides temp sensor values too
#### 3.3.2. DPU_STATE - After DPU OS boots
* DPU updates the DB with additional information such as the reason for every state, and timestamp 
* Carries Die Temp and threshold
* Has reason for previous reboot
* Carries DP, CP up down reasons

DPU_STATE Table

| DPU_STATE | Powered | PCIe_Link | NPU_DPU_Ge_Link | Firmware | OS_boot |  | CtrlPlane | DataPlane |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DPU0 | on | up | up | up | up |  | up | down |
| DPU1 | off | down | down | up | up |  | down | up |
| Genrated By | dpu | dpu | dpu | dpu | dpu |  | dpu | dpu |
| Updated By | ss-pmon | ss-pmon | ss-pmon | ss-pmon  | ss-pmon |  | ss-pmon | ss-pmon |

Potential consumer: Switch CLIs, Utils (install/repair images), HA, LB, Life Cycle Manager 

Use cases: Debuggability, error recovery (reset, power cycle) and fault management, consolidated view of Switch and DPU state/health

#### 3.3.3. End User Reboot Cause Table
This table shows the frame work for DPU reboot-cause reporting

| DPU Reboot Cause | HW/SW | End_User_Message_in_DPU_STATE |
| --- | --- | --- |
| REBOOT_CAUSE_POWER_LOSS | HW | Power failure |
| REBOOT_CAUSE_HOST_DETECT_DPU_FAILURE | SW | Host lost DPU - Try resetting DPU |
| REBOOT_CAUSE_HOST_RECOVER_DPU_FAILURE | SW | Host lost DPU - Power cycled DPU |
| REBOOT_CAUSE_SW_THERMAL |	SW |Switch software Powered Down DPU due to DPU temperature failure |
| PCIE_RESET_CAUSE_SWITCH |	SW | Switch Software Reset DPU PCIe due to PCIe failure |

#### 3.3.3. ChassisStateDB Schema for DPU_STATE
```
Table: “DPU_STATE”

SCHEMA
key:  dpu_state:1
 
HMSET dpu_state:1
        "id": "1",    		#Key itself can be used?
        "powered": "ON",
        "pcie_link_state": "UP",
        "pcie_link_time": "timestamp",
        "pcie_link_reason": "up_down_related string",
        "host_eth_link_state": "UP",
        "host_eth_link_time": " timestamp ",
        "host_eth_link_reason": "up_down_related string",
        "firmware_state": "UP",
        "firmware_time": " timestamp ",
        "firmware_reason": ”gold boot a, ONIE version x",
        "os_state": "UP",
        "os_state_time": "timestamp",
        "os_reason": ”version x",
        "previos_reboot_reason_from_dpu": “Software reboot ”,
        "previos_reboot_time_from_dpu ": “timestamp”,
        “previous_reboot_reason_from_host”: ”Powered Down DPU - Temperature failure”,
        "previos_reboot_time_from_host ": “timestamp”,
        "control_plane_state": ”DOWN",
        "control_plane_time": ”timestamp",
        "control_plane_reason": ”containers restarting",
        "data_plane_state": ”DOWN",
        "data_plane_time": ”timestamp",
        "data_plane_reason": ”Pipeline failure",
```

Besides the state and previous_reboot_reason_from_host other fields will be updated by the DPU once it boots.  The other fields will be updated by the switch from the information read from the hardware registers.

### 3.4.   Midplane Interface

A typical modular chassis includes a midplane-interface to interconnect the Supervisor & line-cards. The same design has been extended in case of a SmartSwitch. The mnic ethernet interface over PCIe which is the midplane-interface, interconnect the Switch Host and the DPUs.

* When DPU card (SLED) or the Supervisor boots and as part of its initialization, midplane interface gets initialized.
* For midplane-interface IP address allocation we will follow the procedure in the [link](https://github.com/sonic-net/SONiC/blob/master/doc/smart-switch/ip-address-assigment/smart-switch-ip-address-assignment.md)

### 3.4.1.    MAC address distribution

* Mac allocation for the Switch Host
    * port X 16 =  512  
        * Example: 28 external ports + 4 internal host-dpu ports
    * default = 8
        * Example: management port, dockers, loopback, midplane-bridge, plus some spare
    * midplane DPU interface host end point X DPUs  = 8
        * Example: 1 per dpu interface

* Mac allocation per DPU
    * default = 8
        * Example: management port, dockers, loopback, 1 for midplane-interface dpu end point, plus some spare
    * application extension = 8
        * Note: 8 mac addresses for future application expansion
 
* Total mac for SmartSwich = (512 + 8 + 8) + ((8 + 8) * 8) =   656 mac addresses

* The MAC address for each host endpoint and the corresponding DPU endpoint will be read from the hardware and updated into the MID_PLANE_IP_MAC table in the ChassisStateDB as shown below. The IP addess will also be stored here for convenience.

### 3.4.2.  ChassisStateDB Schema for MID_PLANE_IP_MAC
```
Table: “MID_PLANE_IP_MAC”

Key: "midplane_interface|dpu0"
            "id”: “1”,
            "host_ip": “169.254.1.2”,
            “host_mac”: “BA:CE:AD:D0:C0:01”, # mac is an example
            "dpu_ip": “169.254.1.1”,
            “dpu_mac”: “BA:CE:AD:D0:D0:01”  # will be updated by the DPU
```

## 3.5. Debuggability & RMA
CLI Extensions and Additions

show platform inventory - shows the SLEDs
<p align="center"><img src="./images/sh-pl-inv.svg"></p>

show platform temperature - shows the DPU temperature
<p align="center"><img src="./images/sh-pl-tmp.svg"></p>

show platform fan - shows the fan speed and status
<p align="center"><img src="./images/sh-pl-fan.svg"></p>

show platform dpu state - will show the dpu status of all DPUs

| DPU_STATE | Powered | PCIe_Link | NPU_DPU_Ge_Link | Firmware | OS_boot |  | CtrlPlane | DataPlane |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DPU0 | on | up | up | up | up |  | up | down |
| DPU1 | off | down | down | up | up |  | down | up |

show platform dpu health (On DPU) - shows the health info of DPU 
<p align="center"><img src="./images/sh-pl-dpu-health.svg"></p>

## 4.   Test Plan
Provide the Link here
