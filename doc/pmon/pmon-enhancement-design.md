# Platform Monitor Enhancement Design #

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo/Kevin Wang      | Initial version                   |
 
## 1. New platform API implememtation
Old platform base APIs will be replaced by new designed API gradually. New API is well structed in a hierarchy style, a root "Platform" class include all the chassis in it, and each chassis will containe all the peripheral devices: PSUs, FANs, SFPs, etc.

As for the vendors, the way to implement the new API will be very similiar, the difference is that individual plugins will be replaced by a "sonic_platform" python package.

New base APIs were added for platform, chassis, watchdog, FAN and PSU. SFP and eeprom not defined yet, will be in next phase. All the APIs defined in the base classes need to be implemented unless there is a limitation(like hardware not support it, see open questions 3)

Previously we have an issue with the old implementation, when adding a new platform API to the base class, have to implement it in all the platform plugins, or at least add a dummy stub to them, or it will fail on the platform that doesn't have it. This will be addressed in the new platfrom API design, not part of the work here.

New platfrom API is defined in this PR: https://github.com/Azure/sonic-platform-common/pull/13

## 2. Export platform related data to DB
Currently when user try to fetch switch peripheral devices related data with CLI, underneath it will directly access hardware via platfrom plugins, in some case it could be very slow, to improvement the performance of these CLI and also for the SNMP maybe, we can collect these data before hand and store them to the DB, and CLI/SNMP will access cached data(DB) instead, which will be much faster.

A common data collection flow for these deamons can be like this: during the boot up of the daemons, it will collect the constant data like serial number, manufature name,.... and for the variable ones (tempreture, voltage, fan speed ....) need to be collected periodically. See below picture.

![](https://github.com/keboliu/SONiC/blob/master/doc/pmon/daemon-flow.svg)

Now we already have a Xcvrd daemon which collect SFP related data periodly from SFP eeprom, we may take Xcvrd as reference and add new deamons(like for PSU, fan, etc.).

PSU daemon need to collect PSU module name, PSU status, and PSU fan speed, etc. PSU deamon will also update the current avalaible PSU numbers and PSU list when there is a PSU change. Fan deamon perform similiar activities as PSU daemon.

Part of transceiver related data already in the DB which are collected by Xcvrd, compare to the output of current "show interface tranceiver" CLI, we may want to add more transceiver data to DB, but it can introduce performace issue to Xcvrd due to the slow response of access SFP eeprom. See open question section.

These daemons will be based on the current platform plugin, will migrate to the new platform APIs in the future.

For the platform hwsku, AISC name, reboot cause and other datas from syseeprom will be write to DB during the start up, it can be done by one of the daemons inside pmon or a seperate task which will exit after collect all of the datas.

Detail datas that need to be collected please see the below DB Schema section.

### 2.1 DB Schema

All the peripheral devices data will be stored in state DB.

#### 2.1.1 Platform Table

    ; Defines information for a platfrom
    key                     = PLATFORM_INFO|platform_name    ; infomation for the chassis
    ; field                 = value
    chassis_num             = INT                            ; chassis number in this platform                        
    chassis_list            = STRING_ARRAY                   ; chassis name list
    
#### 2.1.2 Chassis Table

    ; Defines information for a chassis
    key                     = CHASSIS_INFO|chassis_name      ; infomation for the chassis
    ; field                 = value
    product_name            = STRING                         ; product name from syseeprom
    serial_number           = STRING                         ; serial number from syseeprom
    device_version          = STRING                         ; device version from syseeprom
	base_mac_addr           = STRING                         ; base mac address from syseeprom
	mac_addr_num            = INT                            ; mac address numbers from syseeprom
	manufacture_date        = STRING                         ; manufature date from syseeprom
	manufaturer             = STRING                         ; manufaturer from syseeprom
	platform_name           = STRING                         ; platform name from syseeprom
	onie_version            = STRING                         ; onie version from syseeprom
	crc32_checksum          = INT                            ; CRC-32 checksum from syseeprom
	vendor_ext1             = STRING                         ; vendorextension 1 from syseeprom
	vendor_ext2             = STRING                         ; vendorextension 2 from syseeprom
	vendor_ext3             = STRING                         ; vendorextension 3 from syseeprom
	vendor_ext4             = STRING                         ; vendorextension 4 from syseeprom
	vendor_ext5             = STRING                         ; vendorextension 5 from syseeprom

	reboot_cause            = STRING                         ; most recent reboot cause

	fan_num                 = INT                            ; fan numbers on the chassis
	fan_list                = STRING_ARRAY                   ; fan name list
	psu_num                 = INT                            ; psu numbers on the chassis
	psu_list                = STRING_ARRAY                   ; psu name list

#### 2.1.3 Fan Table

	; Defines information for a fan
	key                     = FAN_INFO|fan_name              ; information for the fan
	; field                 = value
	presence                = BOOLEAN                        ; presence of the fan
	model_num               = STRING                         ; model name of the fan
	serial_num              = STRING                         ; serial number of the fan
	status                  = BOOLEAN                        ; status of the fan
	change_event            = STRING                         ; change event of the fan
	direction               = STRING                         ; direction of the fan 
	speed                   = INT                            ; fan speed
	speed_tolerance         = INT                            ; fan speed tolerance
	speed_target            = INT                            ; fan target speed
	led_status              = STRING                         ; fan led status

#### 2.1.4 Psu Table

	; Defines information for a psu
	key                     = PSU_INFO|psu_name              ; information for the psu
	; field                 = value
	presence                = BOOLEAN                        ; presence of the psu     
	model_num               = STRING                         ; model name of the psu
	serial_num              = STRING                         ; serial number of the psu
	status                  = BOOLEAN                        ; status of the psu
	change_event            = STRING                         ; change event of the psu
	fan_direction           = STRING                         ; direction of the psu fan
	fan_speed               = INT                            ; psu fan speed
	fan_speed_tolerance     = INT                            ; psu fan speed tolerance
	fan_speed_target        = INT                            ; psu fan target speed
	fan_led_status          = STRING                         ; psu fan led status

#### 2.1.5 Watchdog Table

	; Defines information for a watchdog
	key                      = WATCHDOG_INFO|watchdog_name   ; information for the watchdog
	; field                  = value
	arm_status               = BOOLEAN                       ; watchdog arm status
	remaining_time           = INT                           ; watchdog remaining time
	
#### 2.1.6 Transceiver Table

We have a transceiver related information DB schema defined in the Xcvrd daemon design doc: https://github.com/Azure/SONiC/blob/master/doc/xrcvd/transceiver-monitor-hld.md#11-state-db-schema

To align with the output of the current show interface tranceiver we need to extend Transceiver info Table with more informations, as below:

        Connector: No separable connector
        Encoding: Unspecified
        Extended Identifier: Power Class 1(1.5W max)
        Extended RateSelect Compliance: QSFP+ Rate Select Version 1
        Length Cable Assembly(m): 1
        Nominal Bit Rate(100Mbs): 255
        Specification compliance:
                10/40G Ethernet Compliance Code: 40GBASE-CR4
        Vendor Date Code(YYYY-MM-DD Lot): 2016-01-19 
        Vendor OUI: 00-02-c9

New Transceiver info Table schema will be:

	; Defines Transceiver information for a port
	key                         = TRANSCEIVER_INFO|ifname          ; information for SFP on port
	; field                     = value
	type                        = 1*255VCHAR                       ; type of sfp
	hardwarerev                 = 1*255VCHAR                       ; hardware version of sfp
	serialnum                   = 1*255VCHAR                       ; serial number of the sfp
	manufacturename             = 1*255VCHAR                       ; sfp venndor name
	modelname                   = 1*255VCHAR                       ; sfp model name
	
	Connector                   = 1*255VCHAR                       ; connector information
	encoding                    = 1*255VCHAR                       ; encoding information
	ext_identifier              = 1*255VCHAR                       ; extend identifier
	ext_rateselect_compliance   = 1*255VCHAR                       ; extended rateSelect compliance
	cable_length                = INT                              ; cable length in m
	mominal_bit_rate            = INT                              ; nominal bit rate by 100Mbs
	specification_compliance    = 1*255VCHAR                       ; specification compliance
	vendor_date                 = 1*255VCHAR                       ; vendor date
	vendor_oui                  = 1*255VCHAR                       ; vendor OUI

And also lpmode info need to be added to DB, a separated Transceiver lpmode table will be added.

	; Defines Transceiver lpmode information for a port
	key                     = TRANSCEIVER_LPMODE_INFO|ifname   ; lpmode information for SFP on port
	; field                 = value
	lpmode                  = 1*255VCHAR                       ; low power mode, on or off

## 3. Platform monitor related CLI refactoring
### 3.1 change the way that CLI get the data

As described previously, we want to change the way that CLI get the data. Take "show platform psustatus" as an example, behind the scene it's calling psu plugin to access the hardware and get the psu status and print out. In the new design, psu daemon will fetch the psu status and update to DB before hand, thus CLI only need to make use of redis DB APIs and get the informations from the related DB entries.

### 3.2 more output for psu show CLI

original PSU show CLI only provide PSU work status, we should add PSU fan status as well.

Original output:

	admin@sonic# show platform psustatus
	PSU    Status   
	-----  -------- 
	PSU 1  OK       
	PSU 2  NOT OK 
	
New output:

	admin@sonic# show platform psustatus
	PSU    Status   FAN SPEED  FAN DIRECTION
	-----  -------- ---------- --------------
	PSU 1  OK       13417 RPM  Intake 
	PSU 2  OK       12320 RPM  Exhaust
	PSU 3  NOT OK   N/A        N/A
	
### 3.3 new show CLI for fan status

We don't have a CLI for fan status geting yet, new CLI for fan status could be like below, it's adding a new sub command to the "show platform":

	admin@sonic# show platform ?
	Usage: show platform [OPTIONS] COMMAND [ARGS]...

	  Show platform-specific hardware info

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  fanstatus  Show fan status information
	  mlnx       Mellanox platform specific configuration...
	  psustatus  Show PSU status information
	  summary    Show hardware platform information
	  syseeprom  Show system EEPROM information
The output of the command is like below:

	admin@sonic# show platform fanstatus
	FAN    SPEED      Direction
	-----  ---------  ---------
	FAN 1  12919 RPM  Intake
	FAN 2  13043 RPM  Exhaust
	
### 3.4 new show CLI for watchdog status

Same as for fan status we add a new sub command to the "show platform":

	admin@sonic# show platform ?
	Usage: show platform [OPTIONS] COMMAND [ARGS]...

	  Show platform-specific hardware info

	Options:
	  -?, -h, --help  Show this message and exit.

	Commands:
	  fanstatus  Show fan status information
	  mlnx       Mellanox platform specific configuration...
	  psustatus  Show PSU status information
	  summary    Show hardware platform information
	  syseeprom  Show system EEPROM information
	  watchdog   Show watchdog status
The output of the command is like below:

	admin@sonic# show platform watchdog
	ARM STATUS  EXPIRE TIME
	----------  -----------
	ARMED       3s

### 3.5 Transceiver related CLI refactoring

Currently Transceiver related CLI is fetching infomation by directly access the SFP eeprom, the output will keep as original, and information will be fetched from state DB.

### 3.6 Utilities for real-time data

For the sfputility, psuutility, user may want to keep a way to get real-time data from hardware rather than from DB for debug purpose, so we may keep sfputility, psuutility and only install them in pmon.

## 4. Pmon daemons dynamically loading
We have multi pmon daemons for different peripheral devices, like xcvrd for transceivers, ledd for front panel LEDs, etc. Later on we may add more for PSU, fan.

But not all the platfrom can support all of these daemons due to various reasons, in some case some platform may need some special daemons which are not common.

Thus if we only load the common pmon daemons in all the platfrom without any determination, may encounter into some errors. To avoid this, pmon need a capability to load the daemons dynamically based on specific platfrom.

The starting of the daemons inside pmon is controlled by supervisord, to have dynamically control on it, an approach is to manipulate supervisord. For now pmon superviosrd have a common configuration file which applied to all the platforms by default.

We can add a customized pmon daemon configuration file in the platform folder, make the enhance start script "start.sh" with a parser for this configuration file, and load the daemons conditionally according to the parse result. For example, to control the ledd, we can put a file "leed_not_start" to platform folder, when dectect this file exist, it will not start ledd:

	if [ ! -e /usr/share/sonic/platform/leed_not_start ]; then
		supervisorctl start ledd
	fi
	
## 5. Open Questions
- 1.) Do we need a watchdog daemon?
- 2.) Make xcvrd collect more information (lpmode) may degrade the performance.
