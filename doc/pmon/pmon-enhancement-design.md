# Platform Monitor Enhancement Design #

### Rev 0.1 ###

### Revision ###

 | Rev |     Date    |       Author       | Change Description                |
 |:---:|:-----------:|:------------------:|-----------------------------------|
 | 0.1 |             |      Liu Kebo/Kevin Wang      | Initial version                   |


  
## 1. Optimize platform related data access

In current implementation when user try to fetch switch peripheral devices related data with CLI, underneath it will directly access hardware via platform plugins, in some case it could be very slow, to improve the performance of these CLI and SNMP, we can collect these data before hand and store them to the DB, CLI/SNMP will access cached data(DB) instead, which will be much faster.

Another benefit of this optimization is that can centralize the platform related data access, DB will be the only source. Direct access to the platform device can only inside the pmon container.

### 1.1 New daemons for PSU and FAN

By now inside pmon container we already have ledd and xcvrd to monitor/control the front panel led and SFP. Similar daemons are needed for PSU and fan. 

#### 1.1.1 Platform device data collection 

One of the main task for these daemons is to post device data to DB. 

PSU daemon need to collect PSU status, PSU fan speed, etc. PSU daemon will also update the current available PSU numbers and PSU list when there is a PSU change. Fan daemon perform similar activities as PSU daemon in terms of data collection.

A common data collection flow for these daemons can be like this: during the boot up of the daemons, it will collect the constant data like serial number, manufacture name, etc. For the variable ones (temperature, voltage, fan speed ....) need to be collected periodically. See below picture.

![](https://github.com/keboliu/SONiC/blob/master/doc/pmon/daemon-flow.svg)

These daemons will be based on the current platform plugin, will migrate to the new platform APIs in the future.

#### 1.1.2 Business logic handling 

Besides data collection these daemons can do some business logic, only generic business logic can be added to these daemons, platform specific logic should not be covered here.  What kind of common logic can be done here is still open, open for suggestion.(open question 2)

#### 1.1.3 Device set operation handling

To handle a set operation, daemon will subscribe to some DB entries and when these is a change, daemon will response the request and call the platform API accordingly.

for FAN and PSU daemons, possible set operation could be  status led and fan speed. 

### 1.2 Xcvrd daemon extension

Part of transceiver related data already in the DB which are collected by Xcvrd, compare to the output of current "show interface transceiver" CLI which get data directly from hardware, Xcvrd need to post more information from eeprom to DB. Detailed list for the new needed information please check following DB schema section. 


### 1.3 Misc platform related data collection

For the platform hwsku, AISC name, reboot cause and other datas from syseeprom will be write to DB during the start up. A new separate task will be added to collect all of the data, since these data will not change over time, so this task doing one shot thing, will exit after post all the data to DB.

Detail datas that need to be collected please see the below DB Schema section.

### 1.4 DB Schema for Platform related data

All the peripheral devices data will be stored in state DB.

#### 1.1.1 Platform Table

    ; Defines information for a platfrom
    key                     = PLATFORM_INFO|platform_name    ; infomation for the chassis
    ; field                 = value                 
    chassis_list            = STRING_ARRAY                   ; chassis name list
    
#### 1.1.2 Chassis Table

	; Defines information for a chassis
	key                     = CHASSIS_INFO|chassis_name      ; infomation for the chassis
	; field                 = value
	presence                = BOOLEAN                        ; presence of the chassis
	model                   = STRING                         ; model number from syseeprom
	serial                  = STRING                         ; serial number from syseeprom
	status                  = STRING                         ; status of the chassis
	change_event            = STRING                         ; change event of chassis
	base_mac_addr           = STRING                         ; base mac address from syseeprom
	reboot_cause            = STRING                         ; most recent reboot cause
	module_num              = INT                            ; module numbers on the chassis
	fan_num                 = INT                            ; fan numbers on the chassis
	psu_num                 = INT                            ; psu numbers on the chassis

	product_name            = STRING                         ; product name from syseeprom
	mac_addr_num            = INT                            ; mac address numbers from syseeprom
	manufacture_date        = STRING                         ; manufature date from syseeprom
	manufacture             = STRING                         ; manufaturer from syseeprom
	platform_name           = STRING                         ; platform name from syseeprom
	onie_version            = STRING                         ; onie version from syseeprom
	crc32_checksum          = INT                            ; CRC-32 checksum from syseeprom
	vendor_ext1             = STRING                         ; vendorextension 1 from syseeprom
	vendor_ext2             = STRING                         ; vendorextension 2 from syseeprom
	vendor_ext3             = STRING                         ; vendorextension 3 from syseeprom
	vendor_ext4             = STRING                         ; vendorextension 4 from syseeprom
	vendor_ext5             = STRING                         ; vendorextension 5 from syseeprom


#### 1.1.3 Fan Table

	; Defines information for a module
	key                     = MODULE_INFO|module_name        ; information for the module
	; field                 = value
	presence                = BOOLEAN                        ; presence of the module
	model                   = STRING                         ; model name of the module
	serial                  = STRING                         ; serial number of the module
	status                  = BOOLEAN                        ; status of the module
	change_event            = STRING                         ; change event of the module
	base_mac_addr           = STRING                         ; base mac address of the module
	fan_num                 = INT                            ; fan numbers on the module
	psu_num                 = INT                            ; psu numbers on the module


#### 1.1.4 PSU Table

	; Defines information for a psu
	key                     = PSU_INFO|psu_name              ; information for the psu
	; field                 = value
	presence                = BOOLEAN                        ; presence of the psu     
	model                   = STRING                         ; model name of the psu
	serial                  = STRING                         ; serial number of the psu
	status                  = BOOLEAN                        ; status of the psu
	change_event            = STRING                         ; change event of the psu
	fan                     = STRING                         ; fan_name of the psu
	led_status              = STRING                         ; led status of the psu


	
#### 1.1.6 Transceiver Table

We have a transceiver related information DB schema defined in the [Xcvrd daemon design doc](https://github.com/Azure/SONiC/blob/master/doc/xrcvd/transceiver-monitor-hld.md#11-state-db-schema).

To align with the output of the current show interface transceiver we need to extend Transceiver info Table with more information, as below:

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

## 2. Platform monitor related CLI and SNMP Agent re-factoring
### 2.1 change the way that CLI/SNMP Agent get the data

As described previously, we want to change the way that CLI/SNMP Agent get the data. Take "show platform psustatus" as an example, behind the scene it's calling psu plugin to access the hardware and get the psu status and print out. In the new design, psu daemon will fetch the psu status and update to DB before hand, thus CLI only need to connect to state DB get the information from the related DB entries.

New CLI/SNMP Agent flow described as below picture:
![](https://github.com/keboliu/SONiC/blob/master/doc/pmon/CLI-SNMP-flow.svg)


### 2.2 more output for psu show CLI

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
	
### 2.3 new show CLI for fan status

We don't have a CLI for fan status getting yet, new CLI for fan status could be like below, it's adding a new sub command to the "show platform":

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
	
### 2.4 new show CLI for watchdog status

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

### 2.5 Transceiver related CLI re-factoring

Currently Transceiver related CLI is fetching information by directly access the SFP eeprom, the output will keep as original, and the source will be changed to state DB.

### 2.6 PSU SNMP Agent re-factoring

After PSU status data post to state DB, SNMP agent will get PSU data from state DB instead of directly call platform psu plugin, related code in class [PowerStatusHandler](https://github.com/Azure/sonic-snmpagent/blob/master/src/sonic_ax_impl/mibs/vendor/cisco/ciscoEntityFruControlMIB.py#L13) will be changed accordingly. [PhysicalTableMIBUpdater](https://github.com/Azure/sonic-snmpagent/blob/master/src/sonic_ax_impl/mibs/ietf/rfc2737.py#L113) is a good example for updating MIB from state DB.

### 2.7 Utilities for real-time data

For the sfputility, psuutility, user may want to keep a way to get real-time data from hardware rather than from DB for debug purpose, so we may keep sfputility, psuutility and only install them in pmon.

In the future, an approach to get real-time device data from CLI is that when CLI command issued, it will trigger related pmon daemon to fresh the DB data immediately and wait for the pmon daemons to return, then can get the latest device data from DB. This will be considered in the next phase.  

## 3. New platform API implementation

Old platform base APIs will be replaced by new designed API gradually. New API is well structured in a hierarchy style, a root "Platform" class include all the chassis in it, and each chassis will contain all the peripheral devices: PSUs, FANs, SFPs, etc.

As for the vendors, the way to implement the new API will be very similar, the difference is that individual plugins will be replaced by a "sonic_platform" python package.

New base APIs were added for platform, chassis, watchdog, FAN and PSU. SFP and eeprom not defined yet, will be in next phase. All the APIs defined in the base classes need to be implemented unless there is a limitation(like hardware not support it, see open questions 3)

Previously we have an issue with the old implementation, when adding a new platform API to the base class, have to implement it in all the platform plugins, or at least add a dummy stub to them, or it will fail on the platform that doesn't have it. This will be addressed in the new platform API design, not part of the work here.

Design doc for new platform API [design doc](https://github.com/Azure/SONiC/pull/285) and [code implementation PR](https://github.com/Azure/sonic-platform-common/pull/13) are available now. 

## 4. Pmon daemons dynamically loading
We have multi pmon daemons for different peripheral devices, like xcvrd for transceivers, ledd for front panel LEDs, etc. Later on we may add more for PSU, fan.

But not all the platfrom can support(or needed) all of these daemons due to various reasons. Thus if we arbitrarily load all the pmon daemons in all the platfrom, some platform may encounter into some errors. To avoid this, pmon need a capability to load the daemons dynamically for a specific platfrom.

The starting of the daemons inside pmon is controlled by supervisord, to have dynamically control on it, an approach is to manipulate supervisord configuration file. For now pmon superviosrd only have a common configuration file which applied to all the platforms by default.

An pmon config files will be added to the [platform device folder](https://github.com/keboliu/sonic-buildimage/tree/master/device/mellanox/x86_64-mlnx_msn2700-r0) if it want to skip funning some daemon. If no config file found in the folder, by default all the daemons will be started on this platform.  Combine with a template file with above config file, can generate supervisord configuration file for each platform during start up. 


For example, one platform don't want ledd to be started, can add a config file to the platform,
The contenet of the platform specific config filelike below:
           
	"skipped_daemons": {
	    ledd
	}
	   
a common template file for the supervisored config can like below(only show the ledd part)  

	{%- if ledd != "skipped" %}
            [program:ledd]
            command=/usr/bin/ledd
            priority=5
            autostart=false
            autorestart=false
            stdout_logfile=syslog
            stderr_logfile=syslog
            startsecs=0
	{%- endif %}

## 5. Open Questions
- 1. How to get and organize the watchdog data? do we need a watchdog daemon?
- 2. Make xcvrd collect more information (lpmode) may degrade the performance.
- 3. What kind of business logic can be added to the daemons?
