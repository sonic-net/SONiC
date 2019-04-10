
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

# Test Cases

## 1. Ensure that the hw-management service is running properly

This test case is Mellanox specific.

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

## 2. Check platform information

### Steps

* Run `show platform summary`
* Turn off/on PSU from PDU, run `show platform psustatus` respectively
* Run `show platform syseeprom`
* Use the platform specific eeprom.py utility to decode eeprom information in file /bsp/eeprom/vpd_info, compare the result with output of cmd `show platform syseeprom`
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
* The syseeprom info output from cmd `show platform syseeprom` should comply with the info decoded from `/bsp/eeprom/vpd_info`.

### Automation
New automation required

## 3. Run the Sensors automation

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
Covered by existing automation

## 4. Configure SFP and check SFP status

### Steps
* Use the sfputil tool and show command to check SFP status and configure SFP.
  * `sfputil show presence`
  * `show interface transceiver presence`
  * `sfputil show eeprom`
  * `show interface transceiver eeprom`
  * `sfputil reset`

* Use the ethtool to check SFP information, for example `ethtool -m sfp1`
* Check interface status

### Pass/Fail Criteria
* Both `sfputil show presence` and `show interface transceiver presence` should list presence of all ports, for example:
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
* Both `sfputil show eeprom` and `show interface transceiver eeprom` should output eeprom information of all ports. For each port, eeprom information should have format as the example:
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
* The `sfputil reset` command should be successful without error. TODO: need to find out the underlying functionality of resetting sfp, then check accordingly
```
admin@mtbc-sonic-03-2700:~$ sudo sfputil lpmode off Ethernet0
Disabling low-power mode for port Ethernet0...  OK
admin@mtbc-sonic-03-2700:~$ sudo sfputil lpmode on Ethernet0
Enabling low-power mode for port Ethernet0...  OK
admin@mtbc-sonic-03-2700:~$ sudo sfputil reset Ethernet0
Resetting port Ethernet0...  OK
The ethtool command should be able to dump module EEPROM information. Output of the command should have format as below example:
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
* Verify that interface status is not affected after reading of EEPROM

### Automation
New automation required

## 5. Check xcvrd information in DB

### Steps
* Check whether transceiver information of all ports are in redis: `redis-cli -n 6 keys TRANSCEIVER_INFO*`
* Check detailed transceiver information of ports, for example: `redis-cli -n 6 hgetall "TRANSCEIVER_INFO|Ethernet0"`
* Check whether TRANSCEIVER_DOM_SENSOR of all ports in redis: `redis-cli -n 6 keys TRANSCEIVER_DOM_SENSOR*`
* Check detailed TRANSCEIVER_DOM_SENSOR information of ports, for example: `redis-cli -n 6 hgetall "TRANSCEIVER_DOM_SENSOR|Ethernet0"`

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
Ensure that TRANSCEIVER_DOM_SENSOR of all ports are in redis:
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

## 6. Check SYSFS

This test case is Mellanox specific.

### Steps
* Check ASIC temperature: `cat /var/run/hw-management/thermal/asic`
* Check current FAN speed: `cat /var/run/hw-management/thermal/fan1_speed_get`
* Check FAN speed setting: `cat /var/run/hw-management/thermal/pwm1`
* Check other symbolic links under `/var/run/hw-management/thermal`

### Pass/Fail Criteria
* Verify that symbolic links are created under `/var/run/hw-management`. Ensure that there are no invalid symbolic link

### Automation
New automation required

## 7. Verify that `/var/run/hw-management` is mapped to docker pmon

This test case is Mellanox specific.

### Steps
* Go to docker pmon: `docker exec -it pmon /bin/bash`
* Go to `/var/run` of docker container, verify that host directory `/var/run/hw-management` is mapped to docker `pmon`

### Pass/Fail Criteria
* Host directory `/var/run/hw-management` should be mapped to docker pmon

### Automation
New automation required

## 8. Sequential syncd/swss restart

### Steps
* Restart the syncd and swss service:
  * `sudo service syncd restart`
  * `sudo service swss restart`
* After restart, check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers

### Pass/Fail Criteria
* After restart, status of services, interfaces and transceivers should be normal

### Automation
New automation required

## 9. Reload configuration

### Steps
* Reload configuration using: `config load_minigraph -y` and `config reload -y`
* After reload, check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers

### Pass/Fail Criteria
* After reload, status of services, interfaces and transceivers should be normal

### Automation
Partly covered by existing automation. New automation required.

## 10. COLD/WARM/FAST reboot

### Steps
* Perform cold/warm/fast reboot
* Check status of:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
* Check dmesg

### Pass/Fail Criteria
* After reboot, status of services, interfaces and transceivers should be normal
* Verify that there is no error in dmesg

### Automation
Partly covered by existing automation. Need to extend the existing scripts:
* ansible/roles/test/tasks/reboot.yml
* ansible/roles/test/tasks/warm-reboot.yml
* ansible/roles/test/tasks/fast-reboot.yml

## 11. Check thermal sensors output using new OPTIC cables

### Steps
* Plugin new OPTIC cables
* Check the thermal sensors output using command redis-cli -n 6 hgetall "TRANSCEIVER_DOM_SENSOR|Ethernet0"

### Pass/Fail Criteria
* Verify that the thermal sensors could properly detect temperature.

### Automation
Manual intervention required, not automatable

## 12. Manually plug in and pull out PSU modules

### Steps
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Pull out one of the PSU if there are multiple PSU modules available.
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Plug in the PSU module again
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Repeat the test on the other PSU module.

### Pass/Fail Criteria
* Verify that command `show platform psustatus` can correctly indicate the current PSU status.
* Verify that services, interfaces and tranceivers are not affected.
* Verify that CPU and memory usage are at the same level before and after the manual intervention.

### Automation
Manual intervention required, not automatable

## 13. Manually plug in and pull out PSU power cord

### Steps
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Pull out power cord from one of the PSU if there are multiple PSU modules available.
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Plug in the power cord.
* Check PSU status using command `show platform psustatus`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Repeat the test on the other PSU module

### Pass/Fail Criteria
* Verify that command `show platform psustatus` can correctly indicate the current PSU status.
* Verify that services, interfaces and tranceivers are not affected.
* Verify that CPU and memory usage are at the same level before and after the manual intervention.

### Automation
Manual intervention required, not automatable

## 14. Manually plug in and pull out FAN modules

### Steps
* Check FAN status using command `show environment` or `sensors`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Pull out a FAN module if there are multiple FAN modules available.
* Check FAN status using command `show environment` or `sensors`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Plug in the FAN module back.
* Check FAN status using command `show environment` or `sensors`
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Repeat the test on another FAN module

### Pass/Fail Criteria
* Verify that command `show environment` or `sensors` can get correct FAN status and FAN speed
* Verify that services, interfaces and tranceivers are not affected.
* Verify that CPU and memory usage are at the same level before and after the manual intervention.

### Automation
Manual intervention required, not automatable

## 15. Manually plug in and pull out optical cables

### Steps
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Pull out an optical cable.
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage
* Plug in the optical cable back.
* Check:
  * status of services: syncd, swss, hw-management
  * status of interfaces
  * status of transceivers
  * CPU and memory usage

### Pass/Fail Criteria
* Verify that after an interface is pulled out, the corresponding interface is down.
* Verify that after the interface is plugged back, the corresponding interface should recover automatically.
* Verify that syncd, swss and hw-management services are not affected.
* Verify that CPU and memory usage are at the same level before and after the manual intervention.

### Automation
Manual intervention required, not automatable

# Automation Design

This section outlines the design of scripts automating the SONiC platform test cases.

## Entry script

Just like other test cases, plan to have an entry script under ansible/roles/test/tasks:
```
ansible/roles/test/tasks/platform.yml
```

## Scripts for test cases

Multiple sub scripts are used for covering the SONiC platform test cases. The files are started with `test_` and are put under a dedicated folder: `ansible/roles/test/tasks/platform`.

Because these scripts need to be upstreamed, community definitely will have lots of comments. To get feedback early, we can implement the scripts in two phases.

## Scripts to be implemented in phase1

Test Case | Script | Common for all vendors?
----------|--------|-----
1. Ensure that the hw-management service is running properly | ansible/roles/test/tasks/platform/test_hw_mgmt_service.yml | No
2. Check platform information | ansible/roles/test/tasks/platform/test_platform_info.yml | Yes
4. Configure SFP and check SFP status | ansible/roles/test/tasks/platform/test_sfp.yml | Yes
5. Check xcvrd information in DB | ansible/roles/test/tasks/platform/test_xcvr_info_in_db.yml | Yes
6. Check SYSFS | ansible/roles/test/tasks/platform/test_sysfs.yml | No
7. Verify that `/var/run/hw-management` is mapped to docker pmon | ansible/roles/test/tasks/platform/test_sysfs.yml | No

The scripts for testing sensors `ansible/roles/test/tasks/sensors_check.yml` simply calls `ansible/roles/sonic-common/tasks/sensors_check.yml`. In the entry script, we also can call this script to cover sensors testing. No new test case script is required.

## Scripts to be implemented in phase 2

Test Case | Script | Common for all vendors?
----------|--------|-----
8. Sequential syncd/swss restart | ansible/roles/test/tasks/platform/test_restart_swss_syncd.yml | Yes
9. Reload configuration | ansible/roles/test/tasks/platform/test_reload_config.yml | Yes
10.  COLD/WARM/FAST reboot | Extend the existing scripts: <ul><li>ansible/roles/test/tasks/reboot.yml</li><li>ansible/roles/test/tasks/warm-reboot.yml</li><li>ansible/roles/test/tasks/fast-reboot.yml</li></ul>  | Yes

## Reusable scripts

For the tasks that can be reused in testing, they are organnized in separate script files and are put under the same folder `ansible/roles/test/tasks/platform`. The test cases scripts can include the files to use them.

Reusable script | Purpose
--------------|--------------
check_critical_services.yml | Check status of critical services for eg: wss, syncd, bgp, etc. Used by the test cases testing restart/reload/reboot.
check_hw_mgmt_service.yml | Check status of hw-management, thermal control process, fan speed, PWM setting. Used by the test cases testing restart/reload/reboot.
check_interface_status.yml | Check status of interfaces. Used by the test cases testing restart/reload/reboot.
check_sysfs.yml | Check the symbolic links under /var/run/hw-management. Used by the test case testing SYSFS.
check_transceiver_status.yml | Check the status of xcvrd information in DB. Used by the test case testing xcvrd and restart/reload/reboot.

## Upstream strategy

For vendor specific testing, we can use below pattern:

```
- include: mellanox_specific_check_and_test.yml
  when: sonic_asic_type == 'mellanox'
```

Since the entry script needs to call all other test case scripts, all the hw-management scritps should be upstreamed. Each vendor can refactor or improve the test scripts to cover their own platforms.

This pattern can be used in new scripts and in existing scripts that to be expended.
