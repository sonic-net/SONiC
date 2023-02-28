- [Introduction](#introduction)
- [Common Test Cases](#common-test-cases)
  - [1.1 Check platform API implementation](#11-check-platform-api-implementation)
  - [1.2 Check platform-related CLI](#12-check-platform-related-cli)
  - [1.3 Run the Sensors automation](#13-run-the-sensors-automation)
  - [1.4 Check SFP status and configure SFP](#14-check-sfp-status-and-configure-sfp)
  - [1.5 Check xcvrd information in DB](#15-check-xcvrd-information-in-db)
  - [1.6 Sequential syncd/swss restart](#16-sequential-syncdswss-restart)
  - [1.7 Reload configuration](#17-reload-configuration)
  - [1.8 COLD/WARM/FAST/POWER OFF/WATCHDOG reboot](#18-coldwarmfastpower-offwatchdog-reboot)
  - [1.9 Check thermal sensors output using new OPTIC cables](#19-check-thermal-sensors-output-using-new-optic-cables)
  - [1.10 Manually plug in and pull out PSU modules](#110-manually-plug-in-and-pull-out-psu-modules)
  - [1.11 Manually plug in and pull out PSU power cord](#111-manually-plug-in-and-pull-out-psu-power-cord)
  - [1.12 Manually plug in and pull out FAN modules](#112-manually-plug-in-and-pull-out-fan-modules)
  - [1.13 Manually plug in and pull out optical cables](#113-manually-plug-in-and-pull-out-optical-cables)
  - [1.14 Check platform daemon status](#114-check-platform-daemon-status)
- [Mellanox Specific Test Cases](#mellanox-specific-test-cases)
  - [2.1 Ensure that the hw-management service is running properly](#21-ensure-that-the-hw-management-service-is-running-properly)
  - [2.2 Check SFP using ethtool](#22-check-sfp-using-ethtool)
  - [2.3 Check SYSFS](#23-check-sysfs)
  - [2.4 Verify that `/var/run/hw-management` is mapped to docker pmon](#24-verify-that-varrunhw-management-is-mapped-to-docker-pmon)
  - [2.5 Check SFP presence](#25-check-sfp-presence)
- [Automation Design](#automation-design)
  - [Folder Structure and Script Files](#folder-structure-and-script-files)
  - [Scripts to be implemented in phase1](#scripts-to-be-implemented-in-phase1)
  - [Scripts to be implemented in phase 2](#scripts-to-be-implemented-in-phase-2)
  - [Helper scripts](#helper-scripts)
  - [Vendor specific steps](#vendor-specific-steps)

2.5 Check SFP presence
# Introduction

This test plan is to check the functionalities of platform related software components. These software components are for managing platform hardware, including FANs, thermal sensors, SFP, transceivers, pmon, etc.

The software components for managing platform hardware on Mellanox platform is the [hw-management package](https://github.com/Mellanox/hw-mgmt).

To verify that the hw-management package works as expected, the test cases need to be executed on all supported platforms:

* Mellanox ACS-MSN2010
* Mellanox ACS-MSN2100
* Mellanox ACS-MSN2410
* Mellanox ACS-MSN2700
* Mellanox ACS-MSN2740
* Mellanox ACS-MSN3700

The test cases are groupd in two categories:
* Common test cases for all vendors.
* Test cases specific for Mellanox platforms.

In common test cases, some steps are platform dependent. Detailed information will be given in the test cases.

# Common Test Cases

## 1.1 Check platform API implementation

A test suite will install an HTTP server in the PMon container of the DuT. This HTTP server will convert URLs into platform API calls, returning the results of the API call in the HTTP response. All platform API methods will be exercised in this manner, ensuring that:

1. The vendor has implmented the method for the particular platform
2. The API call returned 'sane' data (type is correct, etc.)
3. Where applicable, the data returned is appropriate for the platform being tested (number of fans, number of transceivers, etc.)
4. Where applicable, the data returned is appropriate for the specific DuT (serial number, system EERPOM data, etc.)

## 1.2 Check Platform-Related CLI

This set of tests will verify expected output from all platform-related SONiC CLI commands. The test files will reside in the sonic-mgmt repo under the `tests/platform_tests/cli/` directory.

### Steps

#### Test all subcommands of `show platform`

* Run `show platform summary`
* Turn off/on PSU from PDU (Power Distribution Unit), run `show platform psustatus` respectively. In automation, PDU with programmable interface is required for turning off/on PSU. Without PDU, manual intervention required for this step.

### Pass/Fail Criteria

* `show platform summary` should output these fields: Platform, HwSKU, ASIC, for example:
```
admin@mtbc-sonic-03-2700:~$ show platform summary
Platform: x86_64-mlnx_msn2700-r0
HwSKU: ACS-MSN2700
ASIC: mellanox
```
* PSU status should be `OK` when it is on, `NOT OK` when it is off. Use PDU to turn off/on PSU to verify that correct PSU status can be displayed.
```
admin@mtbc-sonic-03-2700:~$ show platform psustatus
PSU    Status
-----  --------
PSU 1  NOT OK
PSU 2  OK
```
### Automation
New automation required.
The step for turning on/off PSU needs programmable PDU. Need to implement a fixture for turning on/off PSU. When programmable PDU is not available in testbed, this step can only be tested manually. The fixture should be able to return information about whether this capability is supported. If not supported, skip this step in automation.


* Run `show platform syseeprom`
* Use the platform specific eeprom.py utility to directly decode eeprom information from hardware, compare the result with output of cmd `show platform syseeprom`. **This step is platform dependent.** Different eeprom.py utility should be used on different platforms. The below example is taken from Mellanox platform.
```
root@mtbc-sonic-03-2700:~# python
Python 2.7.13 (default, Sep 26 2018, 18:42:22)
[GCC 6.3.0 20170516] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import imp
>>> m = imp.load_source('eeprom', '/usr/share/sonic/device/x86_64-mlnx_msn2740-r0/plugins/eeprom.py')
>>> t = m.board('board', '', '', '')
>>> e = t.read_eeprom()
>>> t.decode_eeprom(e)
TlvInfo Header:
   Id String:    TlvInfo
   Version:      1
   Total Length: 507
TLV Name             Code Len Value
-------------------- ---- --- -----
Product Name         0x21  64 Panther Eth 100
Part Number          0x22  20 MSN2700-CS2F
Serial Number        0x23  24 MT1533X04568
Base MAC Address     0x24   6 E4:1D:2D:F7:D5:5A
Manufacture Date     0x25  19 08/16/2015 22:28:24
Device Version       0x26   1 0
MAC Addresses        0x2A   2 2
Manufacturer         0x2B   8 Mellanox
Vendor Extension     0xFD  36
Vendor Extension     0xFD 164
Vendor Extension     0xFD  36
Vendor Extension     0xFD  36
Vendor Extension     0xFD  36
ONIE Version         0x29  21 2018.05-5.2.0004-9600
CRC-32               0xFE   4 0x371DD10F

>>>
```

### Pass/Fail Criteria

* The syseeprom information should have format as the example:
```
admin@mtbc-sonic-03-2700:~$ show platform syseeprom
TlvInfo Header:
   Id String:    TlvInfo
   Version:      1
   Total Length: 507
TLV Name             Code Len Value
-------------------- ---- --- -----
Product Name         0x21  64 Panther Eth 100
Part Number          0x22  20 MSN2700-CS2F
Serial Number        0x23  24 MT1533X04568
Base MAC Address     0x24   6 E4:1D:2D:F7:D5:5A
Manufacture Date     0x25  19 08/16/2015 22:28:24
Device Version       0x26   1 0
MAC Addresses        0x2A   2 2
Manufacturer         0x2B   8 Mellanox
Vendor Extension     0xFD  36
Vendor Extension     0xFD 164
Vendor Extension     0xFD  36
Vendor Extension     0xFD  36
Vendor Extension     0xFD  36
ONIE Version         0x29  21 2018.05-5.2.0004-9600
CRC-32               0xFE   4 0x371DD10F

(checksum valid)
```
* The syseeprom info output from cmd `show platform syseeprom` should comply with the info decoded using platform specific eeprom.py utility.

### Automation
Covered by existing automation

## 1.3 Run the Sensors automation

### Steps
* Run the sensors automation to ensure that it PASS.
```
$ ansible-playbook test_sonic.yml -i inventory --limit ${SWITCH}-${TOPO} -e testbed_name=${SWITCH}-${TOPO} -e testbed_type=${TOPO} -e testcase_name=sensors -vvvvv
```
For example:
```
$ ansible-playbook test_sonic.yml -i inventory --limit mtbc-sonic-03-2700-t0 -e testbed_name=mtbc-sonic-03-2700-t0 -e testbed_type=t0 -e testcase_name=sensors -vvvvv
```

### Pass/Fail Criteria
The script should PASS

### Automation
Covered by existing automation. In the future, this script could be converted to pytest based code.

## 1.4 Check SFP status and configure SFP

This case is to use the sfputil tool and show command to check SFP status and configure SFP. Currently the the only configuration is to reset SFP.
  * `sfputil show presence`
  * `show interface transceiver presence`
  * `sfputil show eeprom`
  * `show interface transceiver eeprom`
  * `sfputil reset <interface name>`

### Steps
* Get the list of connected ports from `ansible/files/lab_connection_graph.xml`, all connected ports need to be checked.
* Use the `sfputil show presence` and `show interface transceiver presence` commands to check presence of ports.
* Use the `sfputil show eeprom` and `show interface transceiver eeprom` commands to check eeprom information of ports.
* Use the `sfputil reset <interface name>` command to reset each port.
* Use the `show interface status` and `show interface portchannel` commands to check interface and port channel status against current topology.

### Pass/Fail Criteria

* Both `sfputil show presence` and `show interface transceiver presence` should list presence of all connected ports, for example:
```
admin@mtbc-sonic-03-2700:~$ sudo sfputil show presence
Port         Presence
-----------  ----------
Ethernet0    Present
Ethernet4    Present
Ethernet8    Present
Ethernet12   Present
...
```
* Both `sfputil show eeprom` and `show interface transceiver eeprom` should output eeprom information of all connected ports. For each port, eeprom information should have format as the example:
```
admin@mtbc-sonic-03-2700:~$ sudo sfputil show eeprom
Ethernet0: SFP EEPROM detected
    Connector: No separable connector
    Encoding: Unspecified
    Extended Identifier: Power Class 1(1.5W max)
    Extended RateSelect Compliance: QSFP+ Rate Select Version 1
    Identifier: QSFP+
    Length Cable Assembly(m): 1
    Nominal Bit Rate(100Mbs): 255
    Specification compliance:
        10/40G Ethernet Compliance Code: 40GBASE-CR4
    Vendor Date Code(YYYY-MM-DD Lot): 2018-08-24
    Vendor Name: Mellanox
    Vendor OUI: 00-02-c9
    Vendor PN: MCP1600-E001
    Vendor Rev: A3
    Vendor SN: MT1834VS04288

...
```
* The `sfputil reset <interface name>` command should be successful without error.
```
admin@mtbc-sonic-03-2700:~$ sudo sfputil reset Ethernet0
Resetting port Ethernet0...  OK
```
* Verify that interface status is not affected after reading of EEPROM. Up and down status of interfaces and port channels should comply with current topology.

### Automation
New automation required

## 1.5 Check xcvrd information in DB
This test case is to verify that xcvrd works as expected by checking transcever information in DB.

### Steps
* Get the list of connected ports from `ansible/files/lab_connection_graph.xml`, all connected ports need to be checked.
* Check whether transceiver information of all ports are in redis: `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* Check detailed transceiver information of each connected port, for example: `redis-cli -n 6 hgetall "TRANSCEIVER_INFO|Ethernet0"`
* Check whether TRANSCEIVER_DOM_SENSOR of all ports in redis: `redis-cli -n 6 keys TRANSCEIVER_DOM_SENSOR*`
* Check detailed TRANSCEIVER_DOM_SENSOR information of each connected ports for example: `redis-cli -n 6 hgetall "TRANSCEIVER_DOM_SENSOR|Ethernet0"`

### Pass/Fail Criteria
* Ensure that transceiver information of all ports are in redis
```
admin@mtbc-sonic-03-2700:~$ redis-cli -n 6 keys TRANSCEIVER_INFO*
 1) "TRANSCEIVER_INFO|Ethernet16"
 2) "TRANSCEIVER_INFO|Ethernet84"
 3) "TRANSCEIVER_INFO|Ethernet40"
 4) "TRANSCEIVER_INFO|Ethernet44"
...
```
* Ensure that detailed transceiver information of a port should be like this example:
```
admin@mtbc-sonic-03-2700:~$ redis-cli -n 6 hgetall "TRANSCEIVER_INFO|Ethernet0"
 1) "type"
 2) "QSFP+"
 3) "hardwarerev"
 4) "A3"
 5) "serialnum"
 6) "MT1834VS04288"
 7) "manufacturename"
 8) "Mellanox"
 9) "modelname"
10) "MCP1600-E001"
```
* Ensure that TRANSCEIVER_DOM_SENSOR of all ports are in redis:
```
admin@mtbc-sonic-03-2700:~$ redis-cli -n 6 keys TRANSCEIVER_DOM_SENSOR*
 1) "TRANSCEIVER_DOM_SENSOR|Ethernet104"
 2) "TRANSCEIVER_DOM_SENSOR|Ethernet88"
 3) "TRANSCEIVER_DOM_SENSOR|Ethernet80"
 4) "TRANSCEIVER_DOM_SENSOR|Ethernet120"
...
```
* Ensure that detailed TRANSCEIVER_DOM_SENSOR information of a port should be like this example:
```
admin@mtbc-sonic-03-2700:~$ redis-cli -n 6 hgetall "TRANSCEIVER_DOM_SENSOR|Ethernet0"
 1) "temperature"
 2) "0.0000"
 3) "voltage"
 4) "0.0000"
 5) "rx1power"
 6) "-inf"
 7) "rx2power"
 8) "-inf"
 9) "rx3power"
10) "-inf"
11) "rx4power"
12) "-inf"
13) "tx1bias"
14) "0.0000"
15) "tx2bias"
16) "0.0000"
17) "tx3bias"
18) "0.0000"
19) "tx4bias"
20) "0.0000"
21) "tx1power"
22) "N/A"
23) "tx2power"
24) "N/A"
25) "tx3power"
26) "N/A"
27) "tx4power"
28) "N/A"
```

### Automation
New automation required

## 1.6 Sequential syncd/swss restart

### Steps
* Restart the syncd and swss service:
  * `sudo service syncd restart`
  * `sudo service swss restart`
* After restart, check:
  * status of services: syncd, swss
    * `sudo systemctl status syncd`
    * `sudo systemctl status swss`
  * status of hw-management - **Mellanox specific**
    * `sudo systemctl status hw-management`
  * status of interfaces and port channels
    * `show interface status`
    * `show interface portchannel`
  * status of transceivers
    * `show interface transcever presence`
    * `redis-cli -n 6 keys TRANSCEIVER_INFO*`

### Pass/Fail Criteria
* After restart, status of services, interfaces and transceivers should be normal:
  * Services syncd and swss should be active(running)
  * Service hw-management should be active(exited) - **Mellanox specific**
  * All interface and port-channel status should comply with current topology.
  * All ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.

### Automation
New automation required

## 1.7 Reload configuration

### Steps
* Reload configuration using: `config load_minigraph -y` and `config reload -y`
* After reload, check:
  * status of services: syncd, swss
    * `sudo systemctl status syncd`
    * `sudo systemctl status swss`
  * status of hw-management - **Mellanox specific**
    * `sudo systemctl status hw-management`
  * status of interfaces and port channels
    * `show interface status`
    * `show interface portchannel`
  * status of transceivers
    * `show interface transcever presence`
    * `redis-cli -n 6 keys TRANSCEIVER_INFO*`

### Pass/Fail Criteria
* After reload, status of services, interfaces and transceivers should be normal:
  * Services syncd and swss should be active(running)
  * Service hw-management should be active(exited) - **Mellanox specific**
  * All interface and port-channel status should comply with current topology.
  * All ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.

### Automation
Partly covered by existing automation. New automation required.

## 1.8 COLD/WARM/FAST/POWER OFF/WATCHDOG reboot

### Steps
* Perform cold/warm/fast/power off/watchdog reboot
  * cold/warm/fast reboot
    * Make use of commands to reboot the switch
  * watchdog reboot
    * Make use of new platform api to reboot the switch
  * power off reboot
    * Make use of PDUs to power on/off DUT.
    * Power on/off the DUT for (number of PSUs + 1) * 2 times
      * Power on each PSU solely
      * Power on all the PSUs simultaneously
      * Delay 5 and 15 seconds between powering off and on in each test
* After reboot, check:
  * status of services: syncd, swss
    * `sudo systemctl status syncd`
    * `sudo systemctl status swss`
  * reboot cause:
    * `show reboot-cause`
  * status of hw-management - **Mellanox specific**
    * `sudo systemctl status hw-management`
  * status of interfaces and port channels
    * `show interface status`
    * `show interface portchannel`
  * status of transceivers
    * `show interface transcever presence`
    * `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* Check dmesg

### Pass/Fail Criteria
* After reboot, status of services, interfaces and transceivers should be normal:
  *  Services syncd and swss should be active(running)
  *  Reboot cause should be correct
  *  Service hw-management should be active(exited) - **Mellanox specific**
  *  All interface and port-channel status should comply with current topology.
  *  All transcevers of ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.
* Verify that there is no error in dmesg

### Automation
Partly covered by existing automation:
* ansible/roles/test/tasks/reboot.yml
* ansible/roles/test/tasks/warm-reboot.yml
* ansible/roles/test/tasks/fast-reboot.yml

Need to re-implement these scripts in pytest and cover the testing in this test case.

## 1.9 Check thermal sensors output using new OPTIC cables

### Steps
* Plug in new OPTIC cables
* Check the thermal sensors output using command `redis-cli -n 6 hgetall "TRANSCEIVER_DOM_SENSOR|Ethernet0"`. Replace 'Ethernet0' in the example with actual interface name.

### Pass/Fail Criteria
* Verify that the thermal sensors could properly detect temperature.

### Automation
Manual intervention required, not automatable

## 1.10 Manually plug in and pull out PSU modules

This test case needs to frequently check various status, the status to be checked and commands for checking them:
* status of services: syncd, swss:
  * `systemctl status syncd`
  * `systemctl status swss`
* status of service: hw-management - **Mellanox specific**
  * `systemctl status hw-management`
* status of interfaces and port channels
  * `show interface status`
  * `show interface portchannel`
* status of transceivers
  * `show interface transcever presence`
  * `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* CPU and memory usage: `top`

Expected results of checking varous status:
* Services syncd and swss should be active(running)
* Service hw-management should be active(exited) - **Mellanox specific**
* All interface and port-channel status should comply with current topology.
* All transcevers of ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.
* Average CPU and memory usage should be at the same level before and after the manual intervention.

### Steps
* Check PSU status using command `show platform psustatus`
* Check various status.
* Pull out one of the PSU if there are multiple PSU modules available.
* Check PSU status using command `show platform psustatus`
* Check various status.
* Plug in the PSU module again
* Check PSU status using command `show platform psustatus`
* Check various status.
* Repeat the test on the other PSU module.

### Pass/Fail Criteria
* Verify that command `show platform psustatus` can correctly indicate the current PSU status.
* Verify that various status are expected after manual intervention. Please refer to the test case description for detailed command for checking status and expected results.

### Automation
Manual intervention required, not automatable

## 1.11 Manually plug in and pull out PSU power cord

This test case needs to frequently check various status, the status to be checked and commands for checking them:
* status of services: syncd, swss:
  * `systemctl status syncd`
  * `systemctl status swss`
* status of service: hw-management - **Mellanox specific**
  * `systemctl status hw-management`
* status of interfaces and port channels
  * `show interface status`
  * `show interface portchannel`
* status of transceivers
  * `show interface transcever presence`
  * `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* CPU and memory usage: `top`

Expected results of checking varous status:
* Services syncd and swss should be active(running)
* Service hw-management should be active(exited) - **Mellanox specific**
* All interface and port-channel status should comply with current topology.
* All transcevers of ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.
* Average CPU and memory usage should be at the same level before and after the manual intervention.

### Steps
* Check PSU status using command `show platform psustatus`
* Check various status.
* Pull out power cord from one of the PSU if there are multiple PSU modules available.
* Check PSU status using command `show platform psustatus`
* Check various status.
* Plug in the power cord.
* Check PSU status using command `show platform psustatus`
* Check various status.
* Repeat the test on the other PSU module

### Pass/Fail Criteria
* Verify that command `show platform psustatus` can correctly indicate the current PSU status.
* Verify that various status are expected after manual intervention. Please refer to the test case description for detailed command for checking status and expected results.

### Automation
Manual intervention required, not automatable

## 1.12 Manually plug in and pull out FAN modules

This test case needs to frequently check various status, the status to be checked and commands for checking them:
* status of services: syncd, swss:
  * `systemctl status syncd`
  * `systemctl status swss`
* status of service: hw-management - **Mellanox specific**
  * `systemctl status hw-management`
* status of interfaces and port channels
  * `show interface status`
  * `show interface portchannel`
* status of transceivers
  * `show interface transcever presence`
  * `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* CPU and memory usage: `top`

Expected results of checking varous status:
* Services syncd and swss should be active(running)
* Service hw-management should be active(exited) - **Mellanox specific**
* All interface and port-channel status should comply with current topology.
* All transcevers of ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) should present.
* Average CPU and memory usage should be at the same level before and after the manual intervention.

### Steps
* Check FAN status using command `show environment` or `sensors`
* Check various status.
* Pull out a FAN module if there are multiple FAN modules available.
* Check FAN status using command `show environment` or `sensors`
* Check various status.
* Plug in the FAN module back.
* Check FAN status using command `show environment` or `sensors`
* Check various status.
* Repeat the test on another FAN module

### Pass/Fail Criteria
* Verify that command `show environment` or `sensors` can get correct FAN status and FAN speed
* Verify that various status are expected after manual intervention. Please refer to the test case description for detailed command for checking status and expected results.

### Automation
Manual intervention required, not automatable

## 1.13 Manually plug in and pull out optical cables

This test case needs to frequently check various status, the status to be checked and commands for checking them:
* status of services: syncd, swss:
  * `systemctl status syncd`
  * `systemctl status swss`
* status of service: hw-management - **Mellanox specific**
  * `systemctl status hw-management`
* status of interfaces and port channels
  * `show interface status`
  * `show interface portchannel`
* status of transceivers
  * `show interface transcever presence`
  * `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* CPU and memory usage: `top`

Expected results of checking varous status:
* Services syncd and swss should be active(running)
* Service hw-management should be active(exited) - **Mellanox specific**
* All interface and port-channel status should comply with current topology and hardware availability:
  * When cable is unplugged, interface should be down. If the interface was the last one in port channel, the port channel should be down as well.
  * After cable is plugged in, interface should be up. If the interface was in port channel, the port channel should be up as well.
* Transcevers of ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) and unplugged should present. Transcever of cable unplugged port should be not present.
* Average CPU and memory usage should be at the same level before and after the manual intervention.

### Steps
* Check various status.
* Pull out an optical cable.
* Check various status.
* Plug in the optical cable back.
* Check various status.

### Pass/Fail Criteria
* Verify that after an interface is pulled out, the corresponding interface is down.
* Verify that after the interface is plugged back, the corresponding interface should recover automatically.
* Verify that syncd, swss and hw-management services are not affected.
* Verify that CPU and memory usage are at the same level before and after the manual intervention.

### Automation
Manual intervention required, not automatable

## 1.14 Check platform daemon status

This test case will check the all daemon running status inside pmon(ledd no included) if they are supposed to to be running on this platform.
* Using command `docker exec pmon supervisorctl status | grep {daemon}` to get the status of the daemon

Expected results of checking daemon status:
* the status of the daemon should be `RUNNING`

### Steps
* Get the running daemon list from the configuration file `/usr/share/sonic/device/{platform}/{hwsku}/pmon_daemon_control.json`
* Check all the daemons running status in the daemon list

### Pass/Fail Criteria
* All the daemon status in the list shall be `RUNNING`

# Mellanox Specific Test Cases

## 2.1 Ensure that the hw-management service is running properly

### Steps

* Check service status using `systemctl status hw-management`.
* Check the thermal control daemon: `ps -ef | grep therma-control`
* Check thermal control status: `cat /var/run/hw-management/config/suspend`
* Check fan speed setting: `cat /var/run/hw-management/thermal/pwm1`
* Check dmesg

### Pass/Fail Criteria

* The hw-management service should be active and exited.
```
admin@mtbc-sonic-01-2410:~$ sudo systemctl status hw-management
● hw-management.service - Thermal control and chassis management for Mellanox systems
   Loaded: loaded (/lib/systemd/system/hw-management.service; disabled; vendor preset: enabled)
   Active: active (exited) since Wed 2019-04-10 02:04:29 UTC; 4h 14min ago
 Main PID: 362 (code=exited, status=0/SUCCESS)
    Tasks: 2 (limit: 4915)
   Memory: 222.3M
      CPU: 5.001s
   CGroup: /system.slice/hw-management.service
           ├─2667 /bin/bash /usr/bin/hw-management-thermal-control.sh 1 8 2
           └─3434 /bin/sleep 60

Apr 10 02:04:21 mtbc-sonic-01-2410 systemd[1]: Starting Thermal control and chassis management for Mellanox systems...
Apr 10 02:04:29 mtbc-sonic-01-2410 systemd[1]: Started Thermal control and chassis management for Mellanox systems.
Apr 10 02:07:07 mtbc-sonic-01-2410 sh[362]: Mellanox thermal control is started.
Apr 10 02:08:08 mtbc-sonic-01-2410 sh[362]: ASIC thermal zone is disabled due to thermal algorithm is suspend.
Apr 10 02:08:08 mtbc-sonic-01-2410 sh[362]: Set fan speed to 60% percent.
Apr 10 02:08:08 mtbc-sonic-01-2410 sh[362]: Thermal algorithm is manually suspend..
```
* The thermal control daemon should be running:
```
admin@mtbc-sonic-03-2700:~$ ps -ef | grep thermal-control
root 1807 1 0 02:30 ? 00:00:01 /bin/bash /usr/bin/hw-management-thermal-control.sh 1 8 2
```
* Verify that currently thermal control is suspended on SONiC:
```
admin@mtbc-sonic-03-2700:~$ cat /var/run/hw-management/config/suspend
1
```
* Verify that fan speed is set to default 60%. 153/255 = 60%
```
admin@mtbc-sonic-03-2700:~$ cat /var/run/hw-management/thermal/pwm1
153
```
* Verify that there is no error in dmesg

### Automation
New automation Required

## 2.2 Check SFP using ethtool

### Steps
* Use the ethtool to check SFP information, for example `ethtool -m sfp1`. All ports specified in lab connection graph (`ansible/files/lab_connection_graph.xml`) must be checked.
* Check interface status using `show interface status`.

### Pass/Fail Criteria
* The `ethtool` should be able to read information from eeprom of SFP, for example:
```
admin@mtbc-sonic-03-2700:~$ sudo ethtool -m sfp1
    Identifier                                : 0x0d (QSFP+)
    Extended identifier                       : 0x00
    Extended identifier description           : 1.5W max. Power consumption
    Extended identifier description           : No CDR in TX, No CDR in RX
    Extended identifier description           : High Power Class (> 3.5 W) not enabled
    Connector                                 : 0x23 (No separable connector)
    Transceiver codes                         : 0x88 0x00 0x00 0x00 0x00 0x00 0x00 0x00
    Transceiver type                          : 40G Ethernet: 40G Base-CR4
    Transceiver type                          : 100G Ethernet: 100G Base-CR4 or 25G Base-CR CA-L
    Encoding                                  : 0x00 (unspecified)
    BR, Nominal                               : 25500Mbps
    Rate identifier                           : 0x00
    Length (SMF,km)                           : 0km
    Length (OM3 50um)                         : 0m
    Length (OM2 50um)                         : 0m
    Length (OM1 62.5um)                       : 0m
    Length (Copper or Active cable)           : 1m
    Transmitter technology                    : 0xa0 (Copper cable unequalized)
    Attenuation at 2.5GHz                     : 3db
    Attenuation at 5.0GHz                     : 5db
    Attenuation at 7.0GHz                     : 6db
    Attenuation at 12.9GHz                    : 9db
    Vendor name                               : Mellanox
    Vendor OUI                                : 00:02:c9
    Vendor PN                                 : MCP1600-E001
    Vendor rev                                : A3
    Vendor SN                                 : MT1834VS04288
    Revision Compliance                       : SFF-8636 Rev 2.0
    Module temperature                        : 0.00 degrees C / 32.00 degrees F
    Module voltage                            : 0.0000 V
```
* Verify that interface status is not affected after reading of EEPROM. Up and down status of interfaces should comply with current topology design.

### Automation
New automation required

## 2.3 Check SYSFS

### Steps
* Check ASIC temperature: `cat /var/run/hw-management/thermal/asic`
* Check current FAN speed: `cat /var/run/hw-management/thermal/fan1_speed_get`
* Check FAN speed setting: `cat /var/run/hw-management/thermal/pwm1`
* Check other symbolic links under `/var/run/hw-management/thermal`

### Pass/Fail Criteria
* Verify that symbolic links are created under `/var/run/hw-management`. Ensure that there are no invalid symbolic link
* Check current FAN speed against max and min fan speed, also check the the fan speed tolerance, insure it's in the range
* Check thermal valules(CPU, SFP, PSU,...) against the max and min value to make sure they are in the range.

### Automation
New automation required

## 2.4 Verify that `/var/run/hw-management` is mapped to docker pmon

### Steps
* Go to docker pmon: `docker exec -it pmon /bin/bash`
* Go to `/var/run` of docker container, verify that host directory `/var/run/hw-management` is mapped to docker `pmon`

### Pass/Fail Criteria
* Host directory `/var/run/hw-management` should be mapped to docker pmon

### Automation
New automation required

## 2.5 Check SFP presence

### Steps
* Get all the connected interfaces
* Check the presence of the SFP on each interface and corss check the SFP status from the sysfs

### Pass/Fail Criteria
* All th SFP shall be presence and SFP status shall be OK.

### Steps
* Go to docker pmon: `docker exec -it pmon /bin/bash`
* Go to `/var/run` of docker container, verify that host directory `/var/run/hw-management` is mapped to docker `pmon`

### Pass/Fail Criteria
* Host directory `/var/run/hw-management` should be mapped to docker pmon

### Automation
New automation required

# Automation Design

This section outlines the design of scripts automating the SONiC platform test cases. The new pytest-ansible framework will be used. Sample code can be found [here](https://github.com/sonic-net/sonic-mgmt/tree/master/tests).

## Folder Structure and Script Files
The pytest framwork supports flexible test discovery. The plan is to put all platform related scripts under `tests/platform`. Command like `pytest tests/platform` would be able to discover all `test_*.py` and `*_test.py` under `tests/platform`. No entry script is required.

The folder structure and sript files:
```
sonic-mgmt
|-- ansible
|-- tests
    |-- platform
        |-- psu_controller.py
        |-- test_platform_info.py
        |-- test_sfp.py
        |-- test_xcvr_info_in_db.py
        |-- test_sequential_restart.py
        |-- test_reload_config.py
        |-- test_cold_reboot.py
        |-- test_warm_reboot.py
        |-- test_fast_reboot.py
        |-- check_critical_services.py
        |-- check_interface_status.py
        |-- check_transceiver_status.py
        |--mellanox
           |-- test_hw_management_service.py
           |-- test_check_sfp_using_ethtool.py
           |-- test_check_sysfs.py
           |-- check_hw_mgmt_service.py
           |-- mellanox_psu_controller.py
```
Filename of scripts should follow this pattern:
* All scripts for test cases should start with `test_`.
* Put vendor specific test cases in dedicated folder. For example, all Mellanox specific scripts are put under subfolder "mellanox".
* Scripts hold helper functions or classes should start with `check_`, or other prefix as long as it does not conflict with above two patterns.
* The `sonic-mgmt/tests/platform/psu_controller.py` script has the definition of psu_controller fixture that is used in `test_platform_info.py`. The psu_controller fixture returns a PSU controller object for controlling the power on/off to PSUs of DUT. This script also defines the interface of PSU controller object in PsuControllerBase class. Vendor specific PSU controller must be implemented as a sublcass of PsuControllerBase and put under vendor subfolder. For example, Mellanox specific PSU controller is impelemented in `sonic-mgmt/tests/platform/mellanox/mellanox_psu_controller.py`.

With this convention, to run just the common test cases, use below commands:
* `py.test tests/platform/test_* <extra arguments>`

To run common and mellanox specific test cases:
* `py.test tests/platform/test_* tests/platform/mellanox/test_* <extra arguments>`

Please DO NOT use below commands to run tests:
* `py.test tests/platform <extra arguments>`
The reason is that this pattern will recursively collect all the test cases in test_*.py files under tests/platform, including vendor specific subfolders. If there are multiple vendor specific subfolders under this folder, this pattern will try to run all the common and all vendor specific test cases.

Because these scripts need to be upstreamed, community definitely will have lots of comments. To get feedback early, we can implement the scripts in two phases.

## Scripts to be implemented in phase1

| Test Case                                                              | Script                                                  | Common for all vendors? |
|------------------------------------------------------------------------|---------------------------------------------------------|-------------------------|
| Case 1.1 Check platform information                                    | tests/platform/test_platform_info.py                    | Yes                     |
| Case 1.3 Check SFP status and configure SFP                            | tests/platform/test_sfp.py                              | Yes                     |
| Case 1.4 Check xcvrd information in DB                                 | tests/platform/test_xcvr_info_in_db.py                  | Yes                     |
| Case 2.1 Ensure that the hw-management service is running properly     | tests/platform/mellanox/test_hw_management_service.py   | No                      |
| Case 2.2 Check SFP using ethtool                                       | tests/platform/mellanox/test_check_sfp_using_ethtool.py | No                      |
| Case 2.3 Check SYSFS                                                   | tests/platform/mellanox/test_check_sysfs.py             | No                      |
| Case 2.4 Verify that `/var/run/hw-management` is mapped to docker pmon | tests/platform/mellanox/check_sysfs.py                  | No                      |

The psu_controller fixture will also be implemented in phase 1:
* `tests/platform/psu_controller.py`
* `tests/platform/mellanox/mellanox_psu_controller.py`

The scripts for testing sensors `ansible/roles/test/tasks/sensors_check.yml` simply calls `ansible/roles/sonic-common/tasks/sensors_check.yml`. We can conver it to pytest in the future.

## Scripts to be implemented in phase 2

| Test Case                              | Script                                                                                                                                     | Common for all vendors? |
|----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| Case 1.5 Sequential syncd/swss restart | tests/platform/test_sequential_restart.py                                                                                                  | Yes                     |
| Case 1.6 Reload configuration          | tests/platform/test_reload_config.py                                                                                                       | Yes                     |
| Case 1.7  COLD/WARM/FAST reboot        | tests/platform/test_reboot.py | Yes                     |

## Helper scripts

For the tasks that can be reused in testing, they can be organnized into separate helper script files `check_*.py`. The test case scripts can import these helper scripts and call the functions/classes defined in them.

| Reusable script              | Purpose                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| check_critical_services.py  | Check status of critical services for eg: wss, syncd, bgp, etc. Used by the test cases testing restart/reload/reboot.                 |
| check_hw_mgmt_service.py    | Check status of hw-management, thermal control process, fan speed, PWM setting. Used by the test cases testing restart/reload/reboot. |
| check_interface_status.py   | Check status of interfaces. Used by the test cases testing restart/reload/reboot.                                                     |
| check_sysfs.py              | Check the symbolic links under /var/run/hw-management. Used by the test case testing SYSFS.                                           |
| check_transceiver_status.py | Check the status of xcvrd information in DB. Used by the test case testing xcvrd and restart/reload/reboot.                           |

## Vendor specific steps

In common test cases, some steps may be vendor specific. For these steps, we can run different code based on the vendor information derived from the hw-sku. The hw-sku information can be retrieved from minigraph facts. For example:

```python
if sonic_asic_type in ["mellanox"]:
   do_something()
else:
   do_something_else()
```
