# S3IP sysfs specification #

## Table of Content 
 * [1. Table LED enumeration value](#1-table-led-enumeration-value)
 * [2. Temperature sensor sysfs](#2-temperature-sensor-sysfs)
 * [3. Voltage sensor sysfs](#3-voltage-sensor-sysfs)
 * [4. Current sensor sysfs ](#4-current-sensor-sysfs)
 * [5. Syseeprom infomation sysfs ](#5-syseeprom-information-sysfs)
 * [6. Fan information sysfs](#6-fan-information-sysfs)
 * [7. PSU information sysfs](#7-psu-information-sysfs)
 * [8. Transceiver information sysfs](#8-transceiver-information-sysfs)
 * [9. System LED sysfs](#9-system-led-sysfs)
 * [10. FPGA information sysfs](#10-fpga-information-sysfs)
 * [11. CPLD information sysfs](#11-cpld-information-sysfs)
 * [12. Watchdog information sysfs](#12-watchdog-information-sysfs)
 * [13. Slot information sysfs](#13-slot-information-sysfs)
  

### 1. Table LED enumeration value 
| Value  | Description                                       |
|--------|---------------------------------------------------|
| 0      | dark                                              |
| 1      | green                                             |
| 2      | yellow                                            |
| 3      | red                                               |
| 4      | blue                                              |
| 5      | green light flashing                              |
| 6      | yellow light flashing                             |
| 7      | red light flashing                                |
| 8      | blue light flashing                               |

### 2. Temperature sensor sysfs
The Sysfs path for temperature information must be /sys_switch/temp_sensor/

*Table2-1 Temperature Sensor SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/temp_sensor/number| RO| int| equipment the total number of temperature sensors
/sys_switch/temp_sensor/temp[n]/alias| RO| string| identify temperature point location
/sys_switch/temp_sensor/temp[n]/type| RO| string| temperature sensor model
/sys_switch/temp_sensor/temp[n]/max| R/W| int| alarm threshold, unit: millidegree Celsius
/sys_switch/temp_sensor/temp[n]/min| R/W| int| alarm threshold, unit: millidegree Celsius
/sys_switch/temp_sensor/temp[n]/value| RO| int| current temperature, unit: millidegree Celsius

### 3. Voltage sensor sysfs
Voltage Sensor information Sysfs path must be /sys_switch/vol_sensor/

*Table3-1 Voltage Sensor SYSFS property *

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/vol_sensor/number|RO|int|Total number of voltage sensors on the device
/sys_switch/vol_sensor/vol[n]/alias|RO|string|Identifying the location of the voltage sensor
/sys_switch/vol_sensor/vol[n]/type|RO|string|Model of the voltage sensor
/sys_switch/vol_sensor/vol[n]/max|R/W|int|Alarm threshold, unit: mV
/sys_switch/vol_sensor/vol[n]/min|R/W|int|Alarm recovery threshold, unit: mV
/sys_switch/vol_sensor/vol[n]/range|RO|int|Power output error value, such as +-500mV
/sys_switch/vol_sensor/vol[n]/nominal_value|RO|int|Nominal value of supply voltage, unit: mV
/sys_switch/vol_sensor/vol[n]/value|RO|int|Voltage value, unit: mV

### 4. Current sensor sysfs
Current Sensor information Sysfs path must be /sys_switch/curr_sensor/

*Table4-1 Current Sensor SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/curr_sensor/number|RO|int|equipment is the total number of current sensor
/sys_switch/curr_sensor/curr[n]/alias|RO|string|Identifying the location of the current sensor
/sys_switch/curr_sensor/curr[n]/type|RO|string|current sensor model
/sys_switch/curr_sensor/curr[n]/max|R/W|int|Alarm threshold, unit: mA
/sys_switch/curr_sensor/curr[n]/min|R/W|int|Alarm recovery threshold, unit: mA
/sys_switch/curr_sensor/curr[n]/value|RO|int|current unit: mA

### 5. Syseeprom information sysfs
Syseeprom information sysfs path must be /sys_switch/syseeprom

*Table5-1 Syseeprom info SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/syseeprom|RO|int|The file content conforms to the ONIE standard binary

### 6. Fan information sysfs
Fan info Sysfs path must be /sys_switch/fan/

*Table6-1 fan info sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/fan/number |RO| int| The total number of fans in the device
|/sys_switch/fan/fan[n]/model_name |RO| string|fan name
|/sys_switch/fan/fan[n]/serial_number |RO| string|Fan serial number
|/sys_switch/fan/fan[n]/part_number |RO| string|Fan Part Number
|/sys_switch/fan/fan[n]/hardware_version |RO| string|Fan hardware version number
|/sys_switch/fan/fan[n]/motor_number |RO| int| Number of fan motors
|/sys_switch/fan/fan[n]/direction  |RO| enum|The duct types are defined as follows:<br>0: F2B, forward air duct <br>1: B2F, rear duct
|/sys_switch/fan/fan[n]/ratio  |R/W| int| Motor speed percentage, value range 0-100
|/sys_switch/fan/fan[n]/motor[n]/speed |RO| int| Current speed value,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_tolerance |RO| int| Fan Speed Tolerance (Error) ,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_target |RO| int| Motor standard speed value, unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_max |RO| int| Maximum motor speed,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_min |RO| int| Minimum motor speed,unit: RPM
|/sys_switch/fan/fan[n]/status |RO| enum|Fan states are defined as follows:<br>0: not present<br>1: present and normal<br>2: present and abnormal
|/sys_switch/fan/fan[n]/led_status |R/W| enum| The fan status lights are defined as follows:<br>See the definition of enumeration value of LED status light for details

### 7. PSU information sysfs
Power Information The Sysfs path must be /sys_switch/psu/

*Table7-1 Power Information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/psu/number |RO| int| total number of power supplies for the device
|/sys_switch/psu/psu[n]/model_name |RO|  string  | power supply name
|/sys_switch/psu/psu[n]/hardware_version |RO|  string  | power supply hardware version number
|/sys_switch/psu/psu[n]/serial_number |RO|  string  | power supply serial number
|/sys_switch/psu/psu[n]/part_number |RO|  string  | power supply part number
|/sys_switch/psu/psu[n]/type|RO| enum | Power Type: <br>0: DC<br> 1: AC 
|/sys_switch/psu/psu[n]/in_curr |RO|  int | power input current, unit: mA
|/sys_switch/psu/psu[n]/in_vol |RO|  int | power input voltage, unit: mV
|/sys_switch/psu/psu[n]/in_power |RO|  int | power input power, unit: uW
|/sys_switch/psu/psu[n]/out_max_power |RO|  int |The maximum output power of the power supply, unit: uW
|/sys_switch/psu/psu[n]/out_curr |RO|  int | Power supply output current, unit: mA
|/sys_switch/psu/psu[n]/out_vol |RO|  int | power supply output voltage, unit: mV
|/sys_switch/psu/psu[n]/out_power |RO|  int | power supply output power, unit: uW
|/sys_switch/psu/psu[n]/num_temp_sensors |RO|  int | number of temperature sensors
|/sys_switch/psu/psu[n]/temp[n]  | R/W| | reference temperature sensor definition
|/sys_switch/psu/psu[n]/present|RO| enum | state:<br> 0: not present<br>1: Incumbent
|/sys_switch/psu/psu[n]/out_status|RO| enum | Output status, via POWER_OK inside the power supply pin judgment<br>0: abnormal<br>1: normal
|/sys_switch/psu/psu[n]/in_status|RO| enum | Input status, judged by AC_OK pin inside the power supply broken<br>0: abnormal<br>1: normal
|/sys_switch/psu/psu[n]/fan_speed  |RO|  int | power supply fan speed, unit: RPM
|/sys_switch/psu/psu[n]/fan_ratio | R/W|  Int| Power supply fan speed duty cycle
|/sys_switch/psu/psu[n]/led_status|RO|  enum | The power status lights are defined as follows:<br>See the definition of enumeration value of LED status light for details

### 8. Transceiver information sysfs
Transceiver module information Sysfs path must be /sys_switch/transceiver/

*Table8-1 Transceiver module information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switchtransceiver/power_on |R/W| enum |Whether the port of the whole machine is powered on:<br>0: not powered on<br>1: Powered on
|/sys_switchtransceiver/eth[n]/power_on  |R/W| enum |Whether the module is powered on:<br>0: not powered on<br>1: Powered on
|/sys_switchtransceiver/eth[n]/tx_fault|RO| enum |module sending channel exception (including laser/TXCDR)<br>0: normal<br>1: abnormal.<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support;Otherwise, the node must support (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/tx_disable|R/W| enum |Development light<br>0: develop light<br>1: Turn off the light.<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support;Otherwise, the node must support (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/present|RO| enum |is present<br>0: ABSENT, not in place<br>1: OK, present and normal
|/sys_switchtransceiver/eth[n]/rx_los|RO| enum |module does not receive optical signal<br>0: normal<br>1: abnormal.<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support;Otherwise, the node must support (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/reset|R/W| enum |module function reset pin<br>0: no reset<br>1: reset.<br>This information supports exporting (such as QSFP28 standard), the node must support it; otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/low_power_mode|RO| enum |low power mode<br>0: high power<br>1: low power mode.This information supports exporting (such as QSFP28 standard), the node must support it<br>otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/interrupt|RO| enum |Module interrupt flag, indicating whether there is an interrupt<br>0: No interrupt occurred<br>1: Interrupt occurs.<br>This information supports exporting (such as QSFP28 standard), the node must support it; otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switchtransceiver/eth[n]/eeprom |R/W| binary| eeprom compliant with optical module standards

### 9. System LED sysfs
The Sysfs path must be /sys_switch/sysled/

*Table9-1 system LED SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/sysled/sys_led_status|R/W|enum|System LED status, see LED enumeration value table for details
|/sys_switch/sysled/bmc_led_status|R/W|enum|BMC LED status, see LED enumeration value table for details
|/sys_switch/sysled/fan_led_status|R/W|enum|FAN LED status, see LED enumeration value table for details
|/sys_switch/sysled/psu_led_status|R/W|enum|PSU LED status, see LED enumeration value table for details
|/sys_switch/sysled/id_led_status|R/W|enum|Location LED status, see LED enumeration value table for details

### 10. FPGA information sysfs
FPGA Information The Sysfs path must be /sys_switch/fpga/

*Table10-1 FPGA Information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/fpga/number |RO |int| The total number of FPGAs in the device
|/sys_switch/fpga/fpga[n]/alias |RO |string| FPGA alias, bits used to identify the FPGA set
|/sys_switch/fpga/fpga[n]/type |RO |string| FPGA model
|/sys_switch/fpga/fpga[n]/firmware_version |RO |string| FPGA firmware version number
|/sys_switch/fpga/fpga[n]/board_version |RO |string| FPGA hardware version number
|/sys_switch/fpga/fpga[n]/reg_test |R/W |int| Test register, test basic functions available

### 11. CPLD information sysfs
CPLD Information The Sysfs path must be /sys_switch/cpld/

*Table11-1 CPLD information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/cpld/number |RO |int| The total number of CPLDs in the device
|/sys_switch/cpld/cpld[n]/alias |RO |string| CPLD alias, bits used to identify CPLD set
|/sys_switch/cpld/cpld[n]/type |RO |string| CPLD model
|/sys_switch/cpld/cpld[n]/firmware_version |RO |string| CPLD firmware version number
|/sys_switch/cpld/cpld[n]/board_version |RO |string|CPLD hardware version number
|/sys_switch/cpld/cpld[n]/reg_test |R/W |int|Test register, test basic function available

### 12. Watchdog information sysfs
Watchdog information Sysfs path must be /sys_switch/watchdog/

*Table12-1 watchdog information sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/watchdog/identify |RO| string| watchdog identification, eg iTCO_wdt
|/sys_switch/watchdog/enable|R/W|enum|Watchdog Status:<br> 0: inactive state<br>1: Active state
|/sys_switch/watchdog/reset |WO| int | feed dog signal
|/sys_switch/watchdog/timeleft |RO| int | watchdog timeout remaining time, unit:seconds
|/sys_switch/watchdog/timeout|R/W| int | watchdog timeout, unit: seconds

### 13. Slot information sysfs

slot information Sysfs path must be /sys_switch/slot/

*Table13-1 Slot information sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/slot/number|RO| int | number of card slots in the switch
|/sys_switch/slot/slot[n]/model_name |RO| string| slot name
|/sys_switch/slot/slot[n]/hardware_version |RO| string| slot hardware version number
|/sys_switch/slot/slot[n]/serial_number |RO| string| slot serial number
|/sys_switch/slot/slot[n]/part_number |RO| string| slot part number
|/sys_switch/slot/slot[n]/status |RO| string|sub card status<br>0: ABSENT, not in place<br>1: OK, present and normal<br>2: NOT OK, in place and abnormal
|/sys_switch/slot/slot[n]/led_status |R/W| enum| slot status light
|/sys_switch/slot/slot[n]/num_temp_sensors |RO| int| number of temperature sensors on sub card
|/sys_switch/slot/slot[n]/temp_sensor[n] |R/W| |reference temperature sensor definition
|/sys_switch/slot/slot[n]/num_vol_sensors |RO| int| Number of sub card voltage sensors
|/sys_switch/slot/slot[n]/vol_sensor[n] |R/W| |reference voltage sensor definition
|/sys_switch/slot/slot[n]/num_curr_sensors |RO| int| number of sub card current sensors
|/sys_switch/slot/slot[n]/curr_sensor[n] |R/W| |reference current sensor definition
|/sys_switch/slot/slot[n]/num_fpgas |RO| int| number of sub card FPGAs
|/sys_switch/slot/slot[n]/fpga[n] |R/W||Refer to FPGA Information Sysfs Definition
|/sys_switch/slot/slot[n]/num_cplds |RO| int| Number of sub card CPLDs
|/sys_switch/slot/slot[n]/cpld[n] |R/W| |refer to CPLD information Sysfs definition