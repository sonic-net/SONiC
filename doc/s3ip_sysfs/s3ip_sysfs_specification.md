# S3IP sysfs specification #

## Table of Content 
 * [1. LED enumeration value](#1-led-enumeration-value)
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
  

### 1. LED enumeration values 
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
The sysfs path of the temperature sensor information must be /sys_switch/temp_sensor/

*Table2-1 Temperature Sensor SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/temp_sensor/number| RO| int| Total number of temperature sensors
/sys_switch/temp_sensor/temp[n]/alias| RO| string| Identify temperature point location
/sys_switch/temp_sensor/temp[n]/type| RO| string| Temperature sensor model
/sys_switch/temp_sensor/temp[n]/max| R/W| int| Alarm threshold, unit: millidegree Celsius
/sys_switch/temp_sensor/temp[n]/min| R/W| int| Alarm recovery threshold, unit: millidegree Celsius
/sys_switch/temp_sensor/temp[n]/value| RO| int| Current temperature, unit: millidegree Celsius

### 3. Voltage sensor sysfs
The sysfs path of the voltage sensor information must be /sys_switch/vol_sensor/

*Table3-1 Voltage Sensor SYSFS property *

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/vol_sensor/number|RO|int| Total number of voltage sensors
/sys_switch/vol_sensor/vol[n]/alias|RO|string| Identifying the location of the voltage sensor
/sys_switch/vol_sensor/vol[n]/type|RO|string| Model of the voltage sensor
/sys_switch/vol_sensor/vol[n]/max|R/W|int| Alarm threshold, unit: mV
/sys_switch/vol_sensor/vol[n]/min|R/W|int| Alarm recovery threshold, unit: mV
/sys_switch/vol_sensor/vol[n]/range|RO|int| Voltage output error value, such as +-500mV
/sys_switch/vol_sensor/vol[n]/nominal_value|RO|int| Nominal value of supply voltage, unit: mV
/sys_switch/vol_sensor/vol[n]/value|RO|int| Voltage value, unit: mV

### 4. Current sensor sysfs
The sysfs path of the current sensor information must be /sys_switch/curr_sensor/

*Table4-1 Current Sensor SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/curr_sensor/number|RO|int| Total number of current sensors
/sys_switch/curr_sensor/curr[n]/alias|RO|string| Identifying the location of the current sensor
/sys_switch/curr_sensor/curr[n]/type|RO|string| Current sensor model
/sys_switch/curr_sensor/curr[n]/max|R/W|int| Alarm threshold, unit: mA
/sys_switch/curr_sensor/curr[n]/min|R/W|int| Alarm recovery threshold, unit: mA
/sys_switch/curr_sensor/curr[n]/value|RO|int| Current value, unit: mA

### 5. Syseeprom information sysfs
The sysfs path of the syseeprom information must be /sys_switch/syseeprom

*Table5-1 Syseeprom info SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
/sys_switch/syseeprom|RO|int|The file content conforms to the ONIE standard binary

### 6. Fan information sysfs
The sysfs path of the fan information must be /sys_switch/fan/

*Table6-1 fan info sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/fan/number |RO| int| Total number of fans
|/sys_switch/fan/fan[n]/model_name |RO| string| Fan name
|/sys_switch/fan/fan[n]/serial_number |RO| string| Fan serial number
|/sys_switch/fan/fan[n]/part_number |RO| string| Fan Part Number
|/sys_switch/fan/fan[n]/hardware_version |RO| string| Fan hardware version number
|/sys_switch/fan/fan[n]/motor_number |RO| int| Number of fan motors
|/sys_switch/fan/fan[n]/direction  |RO| enum| The duct types are defined as follows:<br>0: F2B, forward air duct <br>1: B2F, rear duct
|/sys_switch/fan/fan[n]/ratio  |R/W| int| Motor speed percentage, value range 0-100
|/sys_switch/fan/fan[n]/motor[n]/speed |RO| int| Speed value,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_tolerance |RO| int| Fan Speed tolerance (error range) ,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_target |RO| int| Motor standard speed value, unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_max |RO| int| Maximum motor speed,unit: RPM
|/sys_switch/fan/fan[n]/motor[n]/speed_min |RO| int| Minimum motor speed,unit: RPM
|/sys_switch/fan/fan[n]/status |RO| enum| Fan states are defined as follows:<br>0: not present<br>1: present and normal<br>2: present and abnormal
|/sys_switch/fan/fan[n]/led_status |R/W| enum| The fan status lights are defined as follows:<br>See the definition of enumeration value of LED status light for details

### 7. PSU information sysfs
The sysfs path of the PSU(Power Supply Unit) information must be /sys_switch/psu/

*Table7-1 Power Information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/psu/number |RO| int| Total number of PSUs
|/sys_switch/psu/psu[n]/model_name |RO|  string  | PSU name
|/sys_switch/psu/psu[n]/hardware_version |RO|  string  | PSU hardware version number
|/sys_switch/psu/psu[n]/serial_number |RO|  string  | PSU serial number
|/sys_switch/psu/psu[n]/part_number |RO|  string  | PSU part number
|/sys_switch/psu/psu[n]/type|RO| enum | PSU Type: <br>0: DC<br> 1: AC 
|/sys_switch/psu/psu[n]/in_curr |RO|  int | PSU input current, unit: mA
|/sys_switch/psu/psu[n]/in_vol |RO|  int | PSU input voltage, unit: mV
|/sys_switch/psu/psu[n]/in_power |RO|  int | PSU input power, compute it from in_curr * in_vol, unit: uW
|/sys_switch/psu/psu[n]/out_max_power |RO|  int |The maximum output power of the PSU, unit: uW
|/sys_switch/psu/psu[n]/out_curr |RO|  int | PSU output current, unit: mA
|/sys_switch/psu/psu[n]/out_vol |RO|  int | PSU output voltage, unit: mV
|/sys_switch/psu/psu[n]/out_power |RO|  int | PSU output power, compute it from out_curr * out_vol, unit: uW
|/sys_switch/psu/psu[n]/num_temp_sensors |RO|  int | Number of temperature sensors
|/sys_switch/psu/psu[n]/temp[n]  | R/W| | Refer to temperature sensor definition
|/sys_switch/psu/psu[n]/num_power_sensors |RO|  int | Number of power sensors, TBD
|/sys_switch/psu/psu[n]/power_sensor[n]  | R/W| | Refer to power sensor definition, TBD
|/sys_switch/psu/psu[n]/present|RO| enum | State:<br> 0: not present<br>1: Incumbent
|/sys_switch/psu/psu[n]/out_status|RO| enum | Output status, via POWER_OK inside the power supply pin judgment<br>0: abnormal<br>1: normal
|/sys_switch/psu/psu[n]/in_status|RO| enum | Input status, judged by AC_OK pin inside the power supply broken<br>0: abnormal<br>1: normal
|/sys_switch/psu/psu[n]/fan_speed  |RO|  int | PSU fan speed, unit: RPM
|/sys_switch/psu/psu[n]/fan_ratio | R/W|  Int| PSU fan speed duty cycle
|/sys_switch/psu/psu[n]/led_status|RO|  enum | The PSU status lights are defined as follows:<br>See the definition of enumeration value of LED status light for details

### 8. Transceiver information sysfs
The sysfs of the transceiver module information must be /sys_switch/transceiver/

*Table8-1 Transceiver module information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/transceiver/power_on |R/W| enum | The power state of all ports on the system:<br>0: power off<br>1: power on
|/sys_switch/transceiver/eth[n]/power_on  |R/W| enum | The power state:<br>0: power off<br>1: power on
|/sys_switch/transceiver/eth[n]/tx_fault|RO| enum |module sending channel exception (including laser/TXCDR)<br>0: normal<br>1: abnormal.<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support;Otherwise, the node must support (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/tx_disable|R/W| enum | Optical signal state<br>0: Turn on the optical signal<br>1: Turn off the optical signal.<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support; Otherwise, the node must support (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/present|RO| enum | Present state<br>0: absent, not in place<br>1: present and normal
|/sys_switch/transceiver/eth[n]/rx_los|RO| enum | Rx loss state(no optical signal received)<br>0: normal<br>1: abnormal<br>This information is exported by eeprom (eg QSFP28 standard), the node may not support;Otherwise, the node must support (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/reset|R/W| enum | Reset pin<br>0: no reset<br>1: reset<br>This information supports exporting (such as QSFP28 standard), the node must support it; otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/low_power_mode|RO| enum | Low power mode state <br>0: high power<br>1: low power mode<br>This information supports exporting (such as QSFP28 standard), the node must support it<br>otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/interrupt|RO| enum | Module interrupt flag, indicating whether there is an interrupt<br>0: No interrupt occurred<br>1: Interrupt occurs<br>This information supports exporting (such as QSFP28 standard), the node must support it; otherwise, the section point may not be supported (such as SFP28 standard)
|/sys_switch/transceiver/eth[n]/eeprom |R/W| binary| eeprom compliant with optical module standards

### 9. System LED sysfs
The sysfs path of the LED state must be /sys_switch/sysled/

*Table9-1 system LED SYSFS property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/sysled/sys_led_status|R/W|enum|System LED status, refer to LED enumeration value table for details
|/sys_switch/sysled/bmc_led_status|R/W|enum|BMC LED status, refer to LED enumeration value table for details
|/sys_switch/sysled/fan_led_status|R/W|enum|FAN LED status, refer to LED enumeration value table for details
|/sys_switch/sysled/psu_led_status|R/W|enum|PSU LED status, refer to LED enumeration value table for details
|/sys_switch/sysled/id_led_status|R/W|enum|Location LED status, refer to LED enumeration value table for details

### 10. FPGA information sysfs
The sysfs path of the FPGA Information must be /sys_switch/fpga/

*Table10-1 FPGA Information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/fpga/number |RO |int| Total number of FPGAs
|/sys_switch/fpga/fpga[n]/alias |RO |string| FPGA alias, Identifying the location of the FPGA
|/sys_switch/fpga/fpga[n]/type |RO |string| FPGA model
|/sys_switch/fpga/fpga[n]/firmware_version |RO |string| FPGA firmware version number
|/sys_switch/fpga/fpga[n]/board_version |RO |string| FPGA hardware version number
|/sys_switch/fpga/fpga[n]/reg_test |R/W |int| Test register, test basic functions available

### 11. CPLD information sysfs
The sysfs path of the CPLD information must be /sys_switch/cpld/

*Table11-1 CPLD information sysfs Property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/cpld/number |RO |int| Total number of CPLDs
|/sys_switch/cpld/cpld[n]/alias |RO |string| CPLD alias, Identifying the location of the CPLD
|/sys_switch/cpld/cpld[n]/type |RO |string| CPLD model
|/sys_switch/cpld/cpld[n]/firmware_version |RO |string| CPLD firmware version number
|/sys_switch/cpld/cpld[n]/board_version |RO |string|CPLD hardware version number
|/sys_switch/cpld/cpld[n]/reg_test |R/W |int|Test register, test basic function available

### 12. Watchdog information sysfs
The sysfs path of the watchdog information must be /sys_switch/watchdog/

*Table12-1 watchdog information sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/watchdog/identify |RO| string| Watchdog identification, eg iTCO_wdt
|/sys_switch/watchdog/enable|R/W|enum| Watchdog Status:<br> 0: inactive<br>1: active
|/sys_switch/watchdog/reset |WO| int | Feed watchdog
|/sys_switch/watchdog/timeleft |RO| int | Watchdog timeout remaining time, unit:seconds
|/sys_switch/watchdog/timeout|R/W| int | Watchdog timeout, unit: seconds

### 13. Slot information sysfs

the sysfs path of slot information must be /sys_switch/slot/

*Table13-1 Slot information sysfs property*

|Sysfs path|Permissions|Data type|Description|
|-|-|-|-|
|/sys_switch/slot/number|RO| int | Total number of card slots
|/sys_switch/slot/slot[n]/model_name |RO| string| Slot name
|/sys_switch/slot/slot[n]/hardware_version |RO| string| Slot hardware version number
|/sys_switch/slot/slot[n]/serial_number |RO| string| Slot serial number
|/sys_switch/slot/slot[n]/part_number |RO| string| Slot part number
|/sys_switch/slot/slot[n]/status |RO| string| Slot status<br>0: ABSENT, not in place<br>1: OK, present and normal<br>2: NOT OK, in place and abnormal
|/sys_switch/slot/slot[n]/led_status |R/W| enum| Slot status light
|/sys_switch/slot/slot[n]/num_temp_sensors |RO| int| Number of temperature sensors on sub card
|/sys_switch/slot/slot[n]/temp_sensor[n] |R/W| | Refer to temperature sensor definition
|/sys_switch/slot/slot[n]/num_vol_sensors |RO| int| Number of sub card voltage sensors
|/sys_switch/slot/slot[n]/vol_sensor[n] |R/W| | Refer to voltage sensor definition
|/sys_switch/slot/slot[n]/num_curr_sensors |RO| int| Number of sub card current sensors
|/sys_switch/slot/slot[n]/curr_sensor[n] |R/W| | Refer to current sensor definition
|/sys_switch/slot/slot[n]/num_fpgas |RO| int| Number of sub card FPGAs
|/sys_switch/slot/slot[n]/fpga[n] |R/W|| Refer to FPGA Information Sysfs Definition
|/sys_switch/slot/slot[n]/num_cplds |RO| int| Number of sub card CPLDs
|/sys_switch/slot/slot[n]/cpld[n] |R/W| | Refer to CPLD information Sysfs definition

### 14. Power sensor sysfs
The sysfs path of the power sensor information must be /sys_switch/power_sensor/
Note:  TBD. This section will be defined in the next stage. Most on-board DC-DC converters (also called PWM or pulse-width modulator chips) provide voltage, current and calculated power. They often provide power In and Power out, allowing easy measurement of efficiency. It is more reliable to read this directly rather than compute it from current * voltage, which might obtain readings at different times and result in invalid computation.  It could also be more accurate because multiplying current * power in the controller results in compound loss of precision(rounded value * rounded value)
